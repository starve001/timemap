package com.mapdex.server;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

/**
 * 数据访问层：从项目根目录的 data/ 与 events.json 读取数据，
 * 按文件 mtime/size 做热更新缓存（改了数据文件无需重启服务）。
 */
@Service
public class DataStore {

    public record EraEntry(int y, String f, String l) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Manifest(String credit, List<EraEntry> eras) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Event(int year, String name, String cat, int importance, String desc, String place) {}

    public record Cached(byte[] body, long mtime, long size) {
        /** 弱 ETag：由 size+mtime 推导而非字节哈希；且强 ETag 会让 Tomcat 拒绝 gzip 压缩 */
        public String etag() {
            return "W/\"" + Long.toHexString(size) + "-" + Long.toHexString(mtime) + "\"";
        }
    }

    private final Path dataDir;
    private final Path eventsFile;
    private final Path contribDir;
    private final ObjectMapper mapper = new ObjectMapper();
    private final ConcurrentHashMap<String, Cached> cache = new ConcurrentHashMap<>();

    private volatile Manifest manifest;
    private volatile long manifestMtime = -1;
    private volatile List<Event> eventList;
    private volatile long eventsMtime = -1;

    /** 社区贡献目录指纹：文件数 + 最大 mtime，变了才重新合并 */
    private record ContribState(int count, long maxMtime) {}

    private volatile ContribState contribState;
    private volatile Cached contribCache;

    public DataStore(@Value("${mapdex.data-dir}") Path dataDir,
                     @Value("${mapdex.events-file}") Path eventsFile,
                     @Value("${mapdex.contrib-dir}") Path contribDir) {
        this.dataDir = dataDir;
        this.eventsFile = eventsFile;
        this.contribDir = contribDir;
    }

    @PostConstruct
    void validate() {
        if (!Files.isDirectory(dataDir)) {
            throw new IllegalStateException("数据目录不存在: " + dataDir.toAbsolutePath()
                    + "（请在项目根目录启动，或用 -Dmapdex.data-dir 指定）");
        }
        manifest();
        events();
        cities();
    }

    public Manifest manifest() {
        Path p = dataDir.resolve("eras").resolve("index.json");
        try {
            long mt = Files.getLastModifiedTime(p).toMillis();
            Manifest cur = manifest;
            if (cur != null && mt == manifestMtime) return cur;
            synchronized (this) {
                long mt2 = Files.getLastModifiedTime(p).toMillis();
                if (manifest == null || mt2 != manifestMtime) {
                    manifest = mapper.readValue(p.toFile(), Manifest.class);
                    manifestMtime = mt2;
                }
                return manifest;
            }
        } catch (IOException e) {
            throw new UncheckedIOException("读取年代清单失败: " + p, e);
        }
    }

    public Cached manifestRaw() {
        return read(dataDir.resolve("eras").resolve("index.json"), "eras/index.json");
    }

    public Cached events() {
        return read(eventsFile, "@events");
    }

    /** 结构化解析事件库（供 AI 工具检索，热更新缓存） */
    public List<Event> eventsParsed() {
        try {
            long mt = Files.getLastModifiedTime(eventsFile).toMillis();
            List<Event> cur = eventList;
            if (cur != null && mt == eventsMtime) return cur;
            synchronized (this) {
                long mt2 = Files.getLastModifiedTime(eventsFile).toMillis();
                if (eventList == null || mt2 != eventsMtime) {
                    eventList = mapper.readValue(eventsFile.toFile(),
                            mapper.getTypeFactory().constructCollectionType(List.class, Event.class));
                    eventsMtime = mt2;
                }
                return eventList;
            }
        } catch (IOException e) {
            throw new UncheckedIOException("解析事件库失败: " + eventsFile, e);
        }
    }

    public Cached cities() {
        return read(dataDir.resolve("cities.json"), "cities.json");
    }

    /** 历史河渠山川（data/geography.json；缺失时返回空集，前端图层自然不出现） */
    public Cached geography() {
        Path p = dataDir.resolve("geography.json");
        if (!Files.exists(p)) {
            try {
                ObjectNode fc = mapper.createObjectNode();
                fc.put("type", "FeatureCollection");
                fc.set("features", mapper.createArrayNode());
                byte[] body = mapper.writeValueAsBytes(fc);
                return new Cached(body, 0, body.length);
            } catch (IOException e) {
                throw new UncheckedIOException("构造空河渠数据失败", e);
            }
        }
        return read(p, "geography.json");
    }

    /** 按年份解析时代切片：取不晚于该年份的最近切片 */
    public EraEntry resolveEra(int year) {
        Manifest m = manifest();
        EraEntry best = null;
        for (EraEntry e : m.eras()) {
            if (e.y() <= year) best = e;
            else break;
        }
        return best != null ? best : m.eras().get(0);
    }

    public Cached eraFile(EraEntry era) {
        return read(dataDir.resolve("eras").resolve(era.f()), "eras/" + era.f());
    }

    /**
     * 社区贡献合并：contributions/&lt;handle&gt;/*.geojson → 单个 FeatureCollection。
     * 目录可不存在（返回空集）；单个坏文件跳过不拖垮整份；入库门禁以
     * tools/validate-contribution.js 为准，这里只做上屏所需的最基础过滤。
     */
    public Cached contributions() {
        List<Path> files = new ArrayList<>();
        if (Files.isDirectory(contribDir)) {
            try (Stream<Path> walk = Files.walk(contribDir)) {
                walk.filter(Files::isRegularFile)
                    .filter(p -> {
                        String n = p.getFileName().toString().toLowerCase();
                        return n.endsWith(".geojson") || n.endsWith(".json");
                    })
                    .forEach(files::add);
            } catch (IOException e) {
                throw new UncheckedIOException("扫描贡献目录失败: " + contribDir, e);
            }
        }
        long maxMtime = 0;
        for (Path p : files) {
            try {
                maxMtime = Math.max(maxMtime, Files.getLastModifiedTime(p).toMillis());
            } catch (IOException ignored) { /* 拿不到 mtime 的文件不参与指纹 */ }
        }
        ContribState st = new ContribState(files.size(), maxMtime);
        synchronized (this) {
            if (contribCache != null && st.equals(contribState)) return contribCache;
            ArrayNode feats = mapper.createArrayNode();
            for (Path p : files) {
                try {
                    JsonNode root = mapper.readTree(p.toFile());
                    if (!"FeatureCollection".equals(root.path("type").asText())) continue;
                    for (JsonNode f : root.path("features")) {
                        String g = f.path("geometry").path("type").asText("");
                        if (g.equals("Point") || g.equals("LineString") || g.equals("Polygon")) feats.add(f);
                    }
                } catch (IOException ignored) { /* 单个坏文件不拖垮整份 */ }
            }
            ObjectNode fc = mapper.createObjectNode();
            fc.put("type", "FeatureCollection");
            fc.set("features", feats);
            byte[] body;
            try {
                body = mapper.writeValueAsBytes(fc);
            } catch (IOException e) {
                throw new UncheckedIOException("合并贡献数据失败", e);
            }
            contribState = st;
            contribCache = new Cached(body, maxMtime, body.length);
            return contribCache;
        }
    }

    private Cached read(Path p, String key) {
        try {
            Path np = p.normalize();
            if (!np.startsWith(dataDir.normalize()) && !np.equals(eventsFile.normalize())) {
                throw new IllegalArgumentException("非法数据路径: " + p);
            }
            long mt = Files.getLastModifiedTime(np).toMillis();
            long sz = Files.size(np);
            Cached c = cache.get(key);
            if (c != null && c.mtime() == mt && c.size() == sz) return c;
            Cached fresh = new Cached(Files.readAllBytes(np), mt, sz);
            cache.put(key, fresh);
            return fresh;
        } catch (IOException e) {
            throw new UncheckedIOException("读取数据文件失败: " + p, e);
        }
    }
}
