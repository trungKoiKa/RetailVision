package vn.retailvision.support;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/**
 * PostgreSQL thật + Mosquitto thật, MQTT bật. Bỏ qua cả lớp nếu máy không có mosquitto.
 * Đóng context sau mỗi lớp: context còn sống giữ client MQTT `backend01` và giành phiên với context của lớp test sau
 * (cùng broker, cùng client id), làm bản tin rơi vào nhầm CSDL.
 */
@SpringBootTest(properties = {"retailvision.mqtt.enabled=true", "retailvision.mqtt.restart-delay-seconds=1"})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
public abstract class MqttPostgresIT extends PostgresIT {

    @BeforeAll
    static void requireMosquitto() {
        Assumptions.assumeTrue(MosquittoBroker.available(), "không tìm thấy mosquitto: bỏ qua test MQTT");
    }

    @DynamicPropertySource
    static void broker(DynamicPropertyRegistry registry) {
        registry.add("retailvision.mqtt.host", () -> "127.0.0.1");
        registry.add("retailvision.mqtt.port", MosquittoBroker::port);
        registry.add("retailvision.mqtt.username", () -> "");
        // client id riêng mỗi context: phiên cleanSession=false trên broker dùng chung không được lẫn bản tin của test khác
        registry.add("retailvision.mqtt.client-id", () -> "backend01-" + java.util.UUID.randomUUID());
    }
}
