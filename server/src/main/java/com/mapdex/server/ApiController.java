package com.mapdex.server;

import org.springframework.http.CacheControl;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;

import java.lang.management.ManagementFactory;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * REST API：
 *   GET /api/meta          元信息（时间范围、数据署名）
 *   GET /api/events        历史事件（含经纬度）
 *   GET /api/cities        历史名城
 *   GET /api/eras          时代切片清单
 *   GET /api/eras/{year}   按年份取政权疆域 GeoJSON（服务端解析最近切片）
 *   GET /healthz           探活
 */
@RestController
public class ApiController {

    private final DataStore store;

    public ApiController(DataStore store) {
        this.store = store;
    }

    @GetMapping(value = "/api/meta", produces = "application/json;charset=UTF-8")
    public Map<String, Object> meta() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("name", "mapdex");
        m.put("yearMin", -221);
        m.put("yearMax", 1918);
        m.put("credit", store.manifest().credit());
        return m;
    }

    @GetMapping(value = "/api/events", produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> events(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.events(), inm);
    }

    @GetMapping(value = "/api/cities", produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> cities(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.cities(), inm);
    }

    @GetMapping(value = "/api/eras", produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> eras(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.manifestRaw(), inm);
    }

    @GetMapping(value = "/api/basemap/{name:.+}", produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> basemap(@PathVariable String name,
                                          @RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.basemap(name), inm);
    }

    @GetMapping(value = "/api/eras/{year}", produces = "application/geo+json;charset=UTF-8")
    public ResponseEntity<byte[]> eraSlice(@PathVariable int year,
                                           @RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.eraFile(store.resolveEra(year)), inm);
    }

    @GetMapping(value = "/healthz", produces = "application/json;charset=UTF-8")
    public Map<String, Object> health() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ok", true);
        m.put("name", "mapdex");
        m.put("uptime", ManagementFactory.getRuntimeMXBean().getUptime() / 1000);
        return m;
    }

    private ResponseEntity<byte[]> serve(DataStore.Cached c, String inm) {
        String etag = c.etag();
        HttpHeaders h = new HttpHeaders();
        h.setCacheControl(CacheControl.noCache());
        h.setETag(etag);
        if (inm != null && inm.contains(etag)) {
            return new ResponseEntity<>(h, HttpStatus.NOT_MODIFIED);
        }
        return new ResponseEntity<>(c.body(), h, HttpStatus.OK);
    }
}