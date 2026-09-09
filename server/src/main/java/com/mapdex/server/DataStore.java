package com.mapdex.server;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 数据访问层：从项目根目录的 data/ 与 events.json 读取数据，
 * 按文件 mtime/size 做热更新缓存（改了数据文件无需重启服务）。
 */
@Service
public class DataStore {

    public record EraEntry(int y, String f, String l) {}

    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Manifest(String credit, List<EraEntry> eras) {}

    public record Cached(byte[] body, long mtime, long size) {
        public String etag() {
            return "\"" + Long.toHexString(size) + "-" + Long.toHexString(mtime) + "\"";
        }
    }

    private final Path dataDir;
    private final Path eventsFile;
    private final ObjectMapper mapper = new ObjectMapper();
    private final ConcurrentHashMap<String, Cached> cache = new ConcurrentHashMap<>();

    private volatile Manifest manifest;
    private volatile long manifestMtime = -1;

    public DataStore(@Value("${mapdex.data-dir}") Path dataDir,
                     @Value("${mapdex.events-file}") Path eventsFile) {
        this.dataDir = dataDir;
        this.eventsFile = eventsFile;
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

    public Cached cities() {
        return read(dataDir.resolve("cities.json"), "cities.json");
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
