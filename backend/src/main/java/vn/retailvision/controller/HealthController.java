package vn.retailvision.controller;

import java.util.Map;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.mqtt.MqttConnectionManager;

/** Sức khoẻ của chính backend: DB và kết nối MQTT. Không nói gì về edge (xem /api/overview). */
@RestController
@RequestMapping("/api/health")
public class HealthController {

    private final JdbcTemplate jdbc;
    private final ObjectProvider<MqttConnectionManager> mqtt;

    public HealthController(JdbcTemplate jdbc, ObjectProvider<MqttConnectionManager> mqtt) {
        this.jdbc = jdbc;
        this.mqtt = mqtt;
    }

    @GetMapping
    public Map<String, Object> health() {
        boolean database;
        try {
            database = Integer.valueOf(1).equals(jdbc.queryForObject("select 1", Integer.class));
        } catch (RuntimeException e) {
            database = false;
        }
        MqttConnectionManager manager = mqtt.getIfAvailable();
        boolean mqttEnabled = manager != null;
        boolean mqttConnected = mqttEnabled && manager.isConnected();
        boolean up = database && (!mqttEnabled || mqttConnected);
        return Map.of(
                "status", up ? "UP" : "DEGRADED",
                "database", database,
                "mqtt", Map.of("enabled", mqttEnabled, "connected", mqttConnected));
    }
}
