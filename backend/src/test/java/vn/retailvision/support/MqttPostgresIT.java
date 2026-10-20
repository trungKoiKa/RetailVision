package vn.retailvision.support;

import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

/** PostgreSQL thật + Mosquitto thật, MQTT bật. Bỏ qua cả lớp nếu máy không có mosquitto. */
@SpringBootTest(properties = {"retailvision.mqtt.enabled=true", "retailvision.mqtt.restart-delay-seconds=1"})
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
    }
}
