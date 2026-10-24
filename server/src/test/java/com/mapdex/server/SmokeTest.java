package com.mapdex.server;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 冒烟测试：不起外部依赖，验证核心接口与数据可用。
 * 数据目录按「仓库根目录」自动定位（Maven 工作目录是 server/，IDE 可能是仓库根）。
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class SmokeTest {

    /** 仓库根目录：包含 data/ 与 events.json */
    private static final Path REPO_ROOT = locateRepoRoot();

    @Autowired
    TestRestTemplate http;

    private final ObjectMapper mapper = new ObjectMapper();

    @DynamicPropertySource
    static void dataProps(DynamicPropertyRegistry reg) {
        reg.add("mapdex.data-dir", () -> REPO_ROOT.resolve("data").toString());
        reg.add("mapdex.events-file", () -> REPO_ROOT.resolve("events.json").toString());
    }

    private static Path locateRepoRoot() {
        Path dir = Paths.get(System.getProperty("user.dir")).toAbsolutePath();
        if (Files.isDirectory(dir.resolve("data"))) return dir;
        if (dir.getParent() != null && Files.isDirectory(dir.getParent().resolve("data"))) {
            return dir.getParent();
        }
        throw new IllegalStateException("定位不到仓库根目录（缺 data/）：从 " + dir + " 起向上查找失败");
    }

    @Test
    void healthzOk() {
        ResponseEntity<String> r = http.getForEntity("/healthz", String.class);
        assertEquals(HttpStatus.OK, r.getStatusCode());
        assertTrue(r.getBody().contains("\"ok\":true"));
    }

    @Test
    void indexServed() {
        ResponseEntity<String> r = http.getForEntity("/", String.class);
        assertEquals(HttpStatus.OK, r.getStatusCode());
        assertTrue(r.getBody().contains("MAPDEX"));
    }

    @Test
    void manifestMatchesSlices() throws Exception {
        // 用前端实际请求的路径（Pages 静态镜像同款）
        ResponseEntity<String> r = http.getForEntity("/api/eras/index.json", String.class);
        assertEquals(HttpStatus.OK, r.getStatusCode());
        JsonNode eras = mapper.readTree(r.getBody()).path("eras");
        assertTrue(eras.isArray() && !eras.isEmpty(), "清单应有切片条目");
        for (JsonNode era : eras) {
            String file = era.path("f").asText();
            assertTrue(Files.isRegularFile(REPO_ROOT.resolve("data/eras").resolve(file)),
                    "切片文件缺失: " + file);
        }
    }

    @Test
    void eraSliceGeoJson() throws Exception {
        ResponseEntity<String> r = http.getForEntity("/api/eras/1200", String.class);
        assertEquals(HttpStatus.OK, r.getStatusCode());
        MediaType ct = r.getHeaders().getContentType();
        assertTrue(ct != null && ct.toString().startsWith("application/geo+json"),
                "Content-Type: " + ct);
        JsonNode fc = mapper.readTree(r.getBody());
        assertEquals("FeatureCollection", fc.path("type").asText());
        assertTrue(fc.path("features").size() > 0, "切片不应为空");
    }

    @Test
    void eraSliceRevalidateWithEtag() {
        ResponseEntity<String> first = http.getForEntity("/api/eras/1200", String.class);
        assertEquals(HttpStatus.OK, first.getStatusCode());
        String etag = first.getHeaders().getETag();
        assertNotNull(etag);
        assertTrue(etag.startsWith("W/"), "应为弱 ETag（强 ETag 会被 Tomcat 拒绝 gzip）");
        HttpHeaders h = new HttpHeaders();
        h.set(HttpHeaders.IF_NONE_MATCH, etag);
        ResponseEntity<String> second = http.exchange("/api/eras/1200", HttpMethod.GET,
                new HttpEntity<>(h), String.class);
        assertEquals(HttpStatus.NOT_MODIFIED, second.getStatusCode());
    }

    @Test
    void eventsAndCities() throws Exception {
        ResponseEntity<String> ev = http.getForEntity("/api/events", String.class);
        assertEquals(HttpStatus.OK, ev.getStatusCode());
        assertTrue(mapper.readTree(ev.getBody()).size() >= 200, "事件库应不少于 200 条");
        ResponseEntity<String> ci = http.getForEntity("/api/cities", String.class);
        assertEquals(HttpStatus.OK, ci.getStatusCode());
        assertTrue(mapper.readTree(ci.getBody()).size() > 0);
    }
}
