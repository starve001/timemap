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
import java.util.concurrent.TimeUnit;

/**
 * REST API：
 *   GET /api/meta          元信息（时间范围、数据署名）
 *   GET /api/events        历史事件（含经纬度）
 *   GET /api/cities        历史名城
 *   GET /api/eras          时代切片清单
 *   GET /api/eras/{year}   按年份取政权疆域 GeoJSON（服务端解析最近切片）
 *   GET /api/contributions 社区贡献合并（contributions/ → 单个 FeatureCollection）
 *   GET /api/geography     历史河渠山川（江河运河随年代显隐）
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

    /** .json 别名：无扩展名路径在 CDN 偶发被卡（实测 123KB 吐 2~8s），带后缀走正常缓存路径 */
    @GetMapping(value = {"/api/events", "/api/events.json"}, produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> events(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.events(), inm);
    }

    @GetMapping(value = {"/api/cities", "/api/cities.json"}, produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> cities(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.cities(), inm);
    }

    // 清单同时兼容 /api/eras 与 /api/eras/index.json：后者是 GitHub Pages
    // 静态镜像的路径（api/eras 需留作切片目录，文件系统不能同名共存）
    @GetMapping(value = {"/api/eras", "/api/eras/index.json"}, produces = "application/json;charset=UTF-8")
    public ResponseEntity<byte[]> eras(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.manifestRaw(), inm);
    }

    @GetMapping(value = "/api/eras/{year}", produces = "application/geo+json;charset=UTF-8")
    public ResponseEntity<byte[]> eraSlice(@PathVariable int year,
                                           @RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.eraFile(store.resolveEra(year)), inm);
    }

    /** 社区贡献合并（contributions/ 缺失或为空时返回空 FeatureCollection） */
    @GetMapping(value = {"/api/contributions", "/api/contributions.json"}, produces = "application/geo+json;charset=UTF-8")
    public ResponseEntity<byte[]> contributions(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.contributions(), inm);
    }

    /** 历史河渠山川：江河、运河随年代显隐，山脉静态走向示意（缺失时返回空集） */
    @GetMapping(value = {"/api/geography", "/api/geography.json"}, produces = "application/geo+json;charset=UTF-8")
    public ResponseEntity<byte[]> geography(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        return serve(store.geography(), inm);
    }

    /** 自托管 Natural Earth 纯自然矢量底图（兼容 MapLibre Worker 的 Accept: application/json） */
    @GetMapping(value = "/api/basemap/natural-earth.geojson",
            produces = {"application/geo+json;charset=UTF-8", "application/json;charset=UTF-8"})
    public ResponseEntity<byte[]> basemapVector(@RequestHeader(value = "If-None-Match", required = false) String inm) {
        DataStore.Cached c = store.basemapVector();
        if (c == null) return ResponseEntity.notFound().build();
        return serve(c, inm);
    }

    /** 自托管 Natural Earth 暗色地形晕渲 WebP 瓦片 */
    @GetMapping(value = "/api/basemap/relief/{z}/{x}/{y}.webp", produces = "image/webp")
    public ResponseEntity<byte[]> basemapRelief(@PathVariable int z,
                                                @PathVariable int x,
                                                @PathVariable int y,
                                                @RequestHeader(value = "If-None-Match", required = false) String inm) {
        DataStore.Cached c = store.basemapReliefTile(z, x, y);
        if (c == null) return ResponseEntity.notFound().build();
        String etag = c.etag();
        HttpHeaders h = new HttpHeaders();
        h.setCacheControl(CacheControl.maxAge(86400, TimeUnit.SECONDS).cachePublic());
        h.setETag(etag);
        if (inm != null && inm.contains(etag)) {
            return new ResponseEntity<>(h, HttpStatus.NOT_MODIFIED);
        }
        return new ResponseEntity<>(c.body(), h, HttpStatus.OK);
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