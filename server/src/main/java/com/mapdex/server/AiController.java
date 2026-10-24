package com.mapdex.server;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * AI 助手接口：
 *   POST /api/ai/chat     对话（{ "message": "..." } → 回答 + 跳转指令）
 *   GET  /api/ai/config   读取当前配置（密钥脱敏）
 *   POST  /api/ai/config   更新 API Key / 模型（{ "apiKey"?, "model"?, "clearKey"? }）
 */
@RestController
public class AiController {

    private static final Logger log = LoggerFactory.getLogger(AiController.class);

    /** 单次提问最大长度：超长文本会原样进入第三方模型的 prompt */
    private static final int MAX_MESSAGE_LEN = 500;

    public record ChatRequest(String message) {}
    public record ConfigRequest(String apiKey, String model, String baseUrl, Boolean clearKey) {}

    private final AiService ai;

    public AiController(AiService ai) {
        this.ai = ai;
    }

    @PostMapping(value = "/api/ai/chat", produces = "application/json;charset=UTF-8")
    public ResponseEntity<?> chat(@RequestBody ChatRequest req) {
        if (req == null || req.message() == null || req.message().isBlank()) {
            return ResponseEntity.badRequest().body(err("消息不能为空"));
        }
        if (req.message().trim().length() > MAX_MESSAGE_LEN) {
            return ResponseEntity.badRequest().body(err("消息过长（最多 " + MAX_MESSAGE_LEN + " 字）"));
        }
        if (!ai.configured()) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(err(
                    "AI 未配置：请点击面板右上角「设置」，填入智谱 API Key（ZHIPU_API_KEY），或设置环境变量后重启。"));
        }
        try {
            return ResponseEntity.ok(ai.chat(req.message().trim()));
        } catch (Exception e) {
            log.error("AI 调用失败", e);
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(err("AI 调用失败: " + brief(e)));
        }
    }

    /** 前端错误提示截断到 200 字：保留可读的排障信息（如 401/余额不足），不回传超长堆栈 */
    private String brief(Exception e) {
        String msg = e.getMessage() == null ? "未知错误" : e.getMessage().trim();
        return msg.length() > 200 ? msg.substring(0, 200) + "…" : msg;
    }

    @GetMapping(value = "/api/ai/config", produces = "application/json;charset=UTF-8")
    public Map<String, Object> config() {
        return ai.configView();
    }

    @PostMapping(value = "/api/ai/config", produces = "application/json;charset=UTF-8")
    public ResponseEntity<?> updateConfig(@RequestBody ConfigRequest req) {
        if (req == null) {
            return ResponseEntity.badRequest().body(err("请求体为空"));
        }
        boolean clearKey = Boolean.TRUE.equals(req.clearKey());
        String apiKey = req.apiKey();
        String model = req.model();
        String baseUrl = req.baseUrl();
        boolean empty = (apiKey == null || apiKey.isBlank())
                && (model == null || model.isBlank())
                && (baseUrl == null || baseUrl.isBlank());
        if (!clearKey && empty) {
            return ResponseEntity.badRequest().body(err("没有需要更新的配置项"));
        }
        ai.updateConfig(apiKey, model, baseUrl, clearKey);
        return ResponseEntity.ok(ai.configView());
    }

    private Map<String, Object> err(String msg) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("error", msg);
        return m;
    }
}