package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.atLeast;
import static org.mockito.Mockito.doCallRealMethod;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.verify;

import java.time.Duration;
import java.util.UUID;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;
import vn.retailvision.dto.mqtt.CrossingMessage;
import vn.retailvision.service.ingestion.IngestionService;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MosquittoBroker;
import vn.retailvision.support.MqttPostgresIT;

/**
 * Backend thật nhận bản tin QoS 1 từ Mosquitto thật. Kiểm các cam kết của thiết kế:
 * chống trùng, bỏ bản tin sai mà không kẹt, và không ack khi DB lỗi để broker gửi lại.
 */
class MqttBrokerIT extends MqttPostgresIT {

    static final String CROSSING_TOPIC = "retailvision/v1/site01/edge01/events/crossing";

    @Autowired
    MqttConnectionManager manager;

    @MockitoSpyBean
    IngestionService ingestion;

    MqttClient publisher;

    @BeforeEach
    void connect() throws MqttException {
        await().atMost(Duration.ofSeconds(10)).until(manager::isConnected);
        publisher = new MqttClient("tcp://127.0.0.1:" + MosquittoBroker.port(), "test-publisher-" + UUID.randomUUID(),
                new MemoryPersistence());
        publisher.connect();
    }

    @AfterEach
    void disconnect() throws MqttException {
        publisher.disconnect();
        publisher.close();
        reset(ingestion);
    }

    private void publishCrossing(byte[] payload) throws MqttException {
        publisher.publish(CROSSING_TOPIC, payload, 1, false);
    }

    @Test
    void qos1CrossingReachesTheDatabase() throws Exception {
        publishCrossing(ContractExamples.validBytes("crossing__in.json"));
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(1));
    }

    @Test
    void sameEventDeliveredTwiceIsStoredOnce() throws Exception {
        byte[] payload = ContractExamples.validBytes("crossing__in.json");
        publishCrossing(payload);
        publishCrossing(payload);
        publishCrossing(payload);
        // một bản tin hợp lệ khác làm mốc: khi nó đã vào DB thì ba bản trước chắc chắn đã được xử lý
        publishCrossing(ContractExamples.text(payload).replace("7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c5e",
                "7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c99").getBytes());
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(2));
    }

    @Test
    void invalidPayloadIsDroppedAndNextValidMessageStillArrives() throws Exception {
        publishCrossing("{\"direction\":\"LEFT\"}".getBytes());
        publishCrossing("khong-phai-json".getBytes());
        publishCrossing(ContractExamples.validBytes("crossing__in.json"));
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(1));
    }

    @Test
    void databaseFailureIsNotAckedAndBrokerRedeliversAfterReconnect() throws Exception {
        // lần xử lý đầu: DB "tắt"; các lần sau: chạy thật
        doThrow(new DataAccessResourceFailureException("db down"))
                .doCallRealMethod()
                .when(ingestion)
                .ingest(any(CrossingMessage.class));

        publishCrossing(ContractExamples.validBytes("crossing__in.json"));

        await().atMost(Duration.ofSeconds(20)).untilAsserted(() -> assertThat(count("crossing_event")).isEqualTo(1));
        verify(ingestion, atLeast(2)).ingest(any(CrossingMessage.class)); // bị gửi lại ít nhất một lần
    }

    @Test
    void healthShowsMqttConnected() {
        assertThat(manager.isConnected()).isTrue();
    }
}
