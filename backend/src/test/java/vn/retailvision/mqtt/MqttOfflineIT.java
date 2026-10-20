package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import java.time.Duration;
import java.util.UUID;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.annotation.DirtiesContext;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MosquittoBroker;
import vn.retailvision.support.MqttPostgresIT;

/**
 * Backend tắt rồi bật lại: broker giữ bản tin QoS 1 cho phiên cleanSession=false (client-id cố định)
 * và giao khi backend nối lại, không mất sự kiện. Làm hỏng context nên chạy tách và dọn sau lớp.
 */
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class MqttOfflineIT extends MqttPostgresIT {

    @Autowired
    MqttConnectionManager manager;

    @Autowired
    RetailVisionProperties props;

    @Autowired
    MqttMessageProcessor processor;

    @Autowired
    MqttRouter router;

    @Test
    void eventsPublishedWhileBackendIsDownAreDeliveredAfterItReconnects() throws Exception {
        await().atMost(Duration.ofSeconds(10)).until(manager::isConnected);
        manager.stop(); // backend tắt (ngắt chủ động); đăng ký và phiên vẫn nằm ở broker

        try (var ignored = new AutoCloseableClient()) {
            // phát khi backend đang tắt
            String base = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"));
            for (int i = 0; i < 3; i++) {
                String id = "7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c0" + i;
                ignored.client.publish(
                        "retailvision/v1/site01/edge01/events/crossing",
                        base.replace("7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c5e", id).getBytes(),
                        1,
                        false);
            }
        }
        Thread.sleep(500);
        assertThat(count("crossing_event")).isZero(); // chưa ai xử lý

        MqttConnectionManager restarted = new MqttConnectionManager(props, processor, router);
        try {
            restarted.start();
            await().atMost(Duration.ofSeconds(15)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(3));
        } finally {
            restarted.stop();
        }
    }

    /** Client phát thử, đóng tự động. */
    private static final class AutoCloseableClient implements AutoCloseable {
        final MqttClient client;

        AutoCloseableClient() throws Exception {
            client = new MqttClient(
                    "tcp://127.0.0.1:" + MosquittoBroker.port(), "offline-publisher-" + UUID.randomUUID(),
                    new MemoryPersistence());
            client.connect();
        }

        @Override
        public void close() throws Exception {
            client.disconnect();
            client.close();
        }
    }
}
