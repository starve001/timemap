package com.mapdex.server;

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
 *   POST /api/ai/config   更新 API Key / 模型（{ "apiKey"?, "model"?, "clearKey"? }）
 */
@RestController
public class AiController {

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
        if (!ai.configured()) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(err(
                    "AI 未配置：请点击面板右上角「设置」，填入智谱 API Key（ZHIPU_API_KEY），或设置环境变量后重启。"));
        }
        try {
            return ResponseEntity.ok(ai.chat(req.message().trim()));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(err("AI 调用失败: " + e.getMessage()));
        }
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