package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import java.time.Duration;
import java.util.UUID;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.DockerMosquitto;
import vn.retailvision.support.PostgresIT;

/**
 * T25 và T17 phía backend với Mosquitto trong Docker (persistence bật, dừng bằng SIGTERM):
 * broker restart khi backend còn chạy, rồi backend tắt + broker restart khi còn hàng đợi.
 * Cả hai phải nhận đủ, không trùng.
 */
@SpringBootTest(properties = {"retailvision.mqtt.enabled=true", "retailvision.mqtt.restart-delay-seconds=1"})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class BrokerRestartIT extends PostgresIT {

    static final DockerMosquitto BROKER = new DockerMosquitto();

    static {
        BROKER.start();
    }

    @AfterAll
    static void stopBroker() {
        BROKER.close();
    }

    @DynamicPropertySource
    static void broker(DynamicPropertyRegistry registry) {
        registry.add("retailvision.mqtt.host", () -> "127.0.0.1");
        registry.add("retailvision.mqtt.port", BROKER::port);
        registry.add("retailvision.mqtt.username", () -> "");
    }

    @Autowired
    MqttConnectionManager manager;

    @Autowired
    RetailVisionProperties props;

    @Autowired
    MqttMessageProcessor processor;

    @Autowired
    MqttRouter router;

    private static byte[] crossing() {
        // mỗi bản tin một event_id riêng
        String base = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"));
        return base.replace("7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c5e", UUID.randomUUID().toString()).getBytes();
    }

    private void publish(int count) throws Exception {
        MqttClient publisher = new MqttClient("tcp://127.0.0.1:" + BROKER.port(), "pub-" + UUID.randomUUID(), new MemoryPersistence());
        publisher.connect();
        for (int i = 0; i < count; i++) {
            publisher.publish("retailvision/v1/site01/edge01/events/crossing", crossing(), 1, false);
        }
        publisher.disconnect();
        publisher.close();
    }

    @Test
    @Order(1)
    void t17_brokerRestartWhileBackendRunsReconnectsResubscribesAndKeepsReceiving() throws Exception {
        await().atMost(Duration.ofSeconds(15)).until(manager::isConnected);
        publish(2);
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(2));

        BROKER.stopGracefully();
        await().atMost(Duration.ofSeconds(10)).until(() -> !manager.isConnected());
        BROKER.restart();
        await().atMost(Duration.ofSeconds(30)).until(manager::isConnected); // Paho tự nối lại

        publish(3);
        await().atMost(Duration.ofSeconds(15)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(5));
    }

    @Test
    @Order(2)
    void t25_backendDownAndBrokerRestartedWithQueuedMessagesDeliversAllWithoutDuplicates() throws Exception {
        long before = count("crossing_event");
        manager.stop(); // backend tắt (ngắt chủ động), phiên cleanSession=false ở lại broker

        publish(5); // phát khi backend đang tắt: nằm trong hàng đợi của broker
        BROKER.stopGracefully(); // restart broker khi còn hàng đợi: phải được ghi xuống đĩa
        BROKER.restart();
        Thread.sleep(500);
        assertThat(count("crossing_event")).isEqualTo(before); // chưa ai xử lý

        MqttConnectionManager restarted = new MqttConnectionManager(props, processor, router);
        try {
            restarted.start();
            await().atMost(Duration.ofSeconds(30)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(before + 5));
            Thread.sleep(2000);
            assertThat(count("crossing_event")).isEqualTo(before + 5); // không nhận thêm, không trùng
        } finally {
            restarted.stop();
        }
    }
}
