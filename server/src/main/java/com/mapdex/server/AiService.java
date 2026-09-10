package com.mapdex.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * AI 助手：LangChain4j + 智谱 GLM（OpenAI 兼容协议）。
 * 职责分工：大模型负责理解用户意图并给出回答，同时输出结构化定位信息
 * （年份 / 事件名）；后端再在本机事件库上做精确匹配，得到可靠的事件索引与年份，
 * 供前端联动地图（goToYear / goToEvent）。
 *
 * 运行时可配置：API Key 与模型可在前端「设置」面板修改，改后立即重建 ChatModel，
 * 并持久化到 mapdex.ai.config-file 指定的 JSON 文件，重启后仍生效。
 */
@Service
public class AiService {

    /** 返回给前端的结果：回答 + 可选跳转指令（事件索引优先，其次年份） */
    public record AiReply(String answer, Integer year, String event, Integer eventIndex) {}

    private static final String SYSTEM_PROMPT = """
            你是「MAPDEX 世界历史时序地图」的智能助手，覆盖公元前 221 年至公元 1918 年的全球政权与历史事件。
            用户可能：1) 用自然语言查询某历史事件或政权所在年份；2) 询问历史知识；3) 要求概括某时段的大事。
            请用简体中文回答，简洁准确。
            最后必须严格输出一个 JSON 对象（不要输出多余文字、不要用 Markdown 代码块、不要加注释），字段如下：
            {"answer":"给用户的回答","year":正整数或负整数或null,"event":"事件名称或null"}
            规则：
            - 若用户想定位到某一年，year 填该年份整数（公元前用负数，如公元前 221 年 = -221）；
            - 若涉及具体历史事件，event 填该事件的名称（尽量与历史事实一致），否则填 null；
            - 未涉及定位时 year 与 event 都为 null。
            """;

    private final DataStore store;
    private final ObjectMapper mapper = new ObjectMapper();
    private final Path configFile;

    // 运行时可改配置（volatile 保证重建后的可见性）
    private volatile String apiKey;
    private volatile String model;
    private volatile String baseUrl;
    private volatile double temperature;
    private volatile ChatModel chatModel;

    public AiService(DataStore store,
                     @Value("${mapdex.ai.api-key}") String apiKey,
                     @Value("${mapdex.ai.base-url}") String baseUrl,
                     @Value("${mapdex.ai.model}") String model,
                     @Value("${mapdex.ai.temperature:0.3}") double temperature,
                     @Value("${mapdex.ai.config-file:}") String configFile) {
        this.store = store;
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
        this.model = model;
        this.temperature = temperature;
        this.configFile = (configFile == null || configFile.isBlank()) ? null : Path.of(configFile);
    }

    @PostConstruct
    void init() {
        loadOverrides();
        rebuild();
    }

    private void loadOverrides() {
        if (configFile == null || !Files.isRegularFile(configFile)) return;
        try {
            JsonNode n = mapper.readTree(configFile.toFile());
            if (n.has("apiKey") && n.get("apiKey").isTextual()) apiKey = n.get("apiKey").asText();
            if (n.has("model") && n.get("model").isTextual()) model = n.get("model").asText();
            if (n.has("baseUrl") && n.get("baseUrl").isTextual()) baseUrl = n.get("baseUrl").asText();
            if (n.has("temperature") && n.get("temperature").isNumber()) temperature = n.get("temperature").asDouble();
        } catch (IOException e) {
            // 配置文件损坏或不可读：忽略，回退到 application.properties 默认值
        }
    }

    private void rebuild() {
        String key = apiKey;
        if (key == null || key.isBlank()) {
            chatModel = null;
            return;
        }
        chatModel = OpenAiChatModel.builder()
                .apiKey(key)
                .baseUrl(baseUrl)
                .modelName(model)
                .temperature(temperature)
                .build();
    }

    public boolean configured() {
        return chatModel != null;
    }

    /** 给前端的非敏感配置视图（密钥脱敏） */
    public Map<String, Object> configView() {
        Map<String, Object> m = new LinkedHashMap<>();
        boolean hasKey = apiKey != null && !apiKey.isBlank();
        m.put("configured", configured());
        m.put("hasKey", hasKey);
        m.put("keyMasked", maskKey());
        m.put("model", model);
        m.put("baseUrl", baseUrl);
        m.put("temperature", temperature);
        return m;
    }

    private String maskKey() {
        String k = apiKey == null ? "" : apiKey.trim();
        if (k.isEmpty()) return "";
        if (k.length() <= 6) return "••••";
        return k.substring(0, 3) + "••••" + k.substring(k.length() - 4);
    }

    /**
     * 更新配置：clearKey 置空密钥；否则仅当传入非空 apiKey 时更新密钥、
     * 传入非空 model 时更新模型、传入非空 baseUrl 时更新网关地址，其余字段保持不变。
     */
    public synchronized void updateConfig(String newApiKey, String newModel, String newBaseUrl, boolean clearKey) {
        if (clearKey) {
            apiKey = "";
        } else if (newApiKey != null && !newApiKey.isBlank()) {
            apiKey = newApiKey.trim();
        }
        if (newModel != null && !newModel.isBlank()) {
            model = newModel.trim();
        }
        if (newBaseUrl != null && !newBaseUrl.isBlank()) {
            String u = newBaseUrl.trim();
            while (u.endsWith("/")) {
                u = u.substring(0, u.length() - 1);
            }
            baseUrl = u;
        }
        rebuild();
        persist();
    }

    private void persist() {
        if (configFile == null) return;
        try {
            if (configFile.getParent() != null) Files.createDirectories(configFile.getParent());
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("apiKey", apiKey == null ? "" : apiKey);
            m.put("model", model);
            m.put("baseUrl", baseUrl);
            m.put("temperature", temperature);
            mapper.writerWithDefaultPrettyPrinter().writeValue(configFile.toFile(), m);
        } catch (IOException e) {
            // 写配置失败不阻断本次会话内生效
        }
    }

    public AiReply chat(String message) {
        if (chatModel == null) {
            throw new IllegalStateException("AI 未启动：缺少 API Key");
        }
        String raw = chatModel.chat(SYSTEM_PROMPT + "\n\n用户问题：" + message);
        return parse(raw);
    }

    private AiReply parse(String raw) {
        String answer = raw;
        Integer year = null;
        String event = null;
        Integer eventIndex = null;
        try {
            JsonNode n = extractJson(raw);
            if (n != null) {
                if (n.has("answer") && n.get("answer").isTextual()) {
                    answer = n.get("answer").asText();
                }
                if (n.has("year") && n.get("year").isIntegralNumber()) {
                    year = n.get("year").asInt();
                }
                if (n.has("event") && n.get("event").isTextual() && !n.get("event").asText().isBlank()) {
                    event = n.get("event").asText().trim();
                }
            }
        } catch (Exception ignore) {
            // 大模型未严格输出 JSON：整体文本作为回答，不定位
        }
        if (event != null) {
            Match m = matchEvent(event, year);
            if (m.index >= 0) {
                event = store.eventsParsed().get(m.index).name();
                eventIndex = m.index;
                year = m.year != Integer.MIN_VALUE ? m.year : year;
            }
        }
        return new AiReply(answer, year, event, eventIndex);
    }

    /** 在事件库中匹配：先精确，再包含；返回事件索引与年份 */
    private Match matchEvent(String name, Integer fallbackYear) {
        List<DataStore.Event> all = store.eventsParsed();
        for (int i = 0; i < all.size(); i++) {
            DataStore.Event e = all.get(i);
            if (e.name() != null && e.name().equals(name)) {
                return new Match(i, e.year());
            }
        }
        int bestIdx = -1;
        int bestYear = Integer.MIN_VALUE;
        for (int i = 0; i < all.size(); i++) {
            DataStore.Event e = all.get(i);
            if (e.name() == null) continue;
            if (e.name().contains(name) || name.contains(e.name())) {
                if (fallbackYear != null && e.year() == fallbackYear) {
                    return new Match(i, e.year());
                }
                if (bestIdx < 0) {
                    bestIdx = i;
                    bestYear = e.year();
                }
            }
        }
        return new Match(bestIdx, bestYear);
    }

    private record Match(int index, int year) {}

    private JsonNode extractJson(String raw) throws Exception {
        String s = raw.trim();
        int a = s.indexOf("```");
        if (a >= 0) {
            int nl = s.indexOf('\n', a);
            int b = s.lastIndexOf("```");
            if (nl >= 0 && b > a) {
                s = s.substring(nl + 1, b).trim();
            }
        }
        int start = s.indexOf('{');
        int end = s.lastIndexOf('}');
        if (start >= 0 && end > start) {
            s = s.substring(start, end + 1);
        }
        return mapper.readTree(s);
    }
}