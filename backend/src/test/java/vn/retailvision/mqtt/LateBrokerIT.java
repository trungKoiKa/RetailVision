package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import java.time.Duration;
import java.util.UUID;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import vn.retailvision.controller.HealthController;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.ControllableMosquitto;
import vn.retailvision.support.PostgresIT;

/** Backend khởi động khi broker chưa chạy: không chết, báo DEGRADED, tự nối khi broker lên rồi nhận bình thường. */
@SpringBootTest(properties = {"retailvision.mqtt.enabled=true", "retailvision.mqtt.restart-delay-seconds=1"})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class LateBrokerIT extends PostgresIT {

    static final ControllableMosquitto BROKER = new ControllableMosquitto();

    @BeforeAll
    static void requireMosquitto() {
        Assumptions.assumeTrue(BROKER.available(), "không có mosquitto");
    }

    @AfterAll
    static void stopBroker() {
        BROKER.close();
    }

    @DynamicPropertySource
    static void broker(DynamicPropertyRegistry registry) {
        registry.add("retailvision.mqtt.host", () -> "127.0.0.1");
        registry.add("retailvision.mqtt.port", BROKER::port); // broker CHƯA chạy lúc context khởi động
        registry.add("retailvision.mqtt.username", () -> "");
    }

    @Autowired
    MqttConnectionManager manager;

    @Autowired
    HealthController health;

    @Test
    void startsWithoutBrokerReportsDegradedThenConnectsWhenBrokerAppears() throws Exception {
        Thread.sleep(2500); // vài lần thử nối thất bại
        assertThat(manager.isConnected()).isFalse();
        assertThat(health.health()).containsEntry("status", "DEGRADED");

        BROKER.start();
        await().atMost(Duration.ofSeconds(20)).until(manager::isConnected);
        assertThat(health.health()).containsEntry("status", "UP");

        MqttClient publisher = new MqttClient("tcp://127.0.0.1:" + BROKER.port(), "pub-" + UUID.randomUUID(), new MemoryPersistence());
        publisher.connect();
        publisher.publish("retailvision/v1/site01/edge01/events/crossing", ContractExamples.validBytes("crossing__in.json"), 1, false);
        publisher.disconnect();
        publisher.close();
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(1));
    }
}
