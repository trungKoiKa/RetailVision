package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import vn.retailvision.dto.request.SettingsRequest;
import vn.retailvision.service.settings.SettingsService;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MosquittoBroker;
import vn.retailvision.support.MqttPostgresIT;

/** P1 qua Mosquitto thật: backend gửi settings/set, nhận settings/result và cập nhật trạng thái yêu cầu. */
class SettingsBrokerIT extends MqttPostgresIT {

    static final String SET_TOPIC = "retailvision/v1/site01/edge01/settings/set";
    static final String RESULT_TOPIC = "retailvision/v1/site01/edge01/settings/result";
    static final String STATE_TOPIC = "retailvision/v1/site01/edge01/state";
    static final ObjectMapper JSON = new ObjectMapper();

    @Autowired
    MqttConnectionManager manager;

    @Autowired
    SettingsService settings;

    @Autowired
    vn.retailvision.service.queue.LiveStateCache live;

    @Test
    void commandReachesTheBrokerAndTheEdgeAnswerResolvesIt() throws Exception {
        await().atMost(Duration.ofSeconds(15)).until(manager::isConnected);
        live.clear();

        MqttClient edge = new MqttClient("tcp://127.0.0.1:" + MosquittoBroker.port(), "fake-edge-" + UUID.randomUUID(), new MemoryPersistence());
        List<byte[]> commands = new CopyOnWriteArrayList<>();
        edge.setCallback(new org.eclipse.paho.client.mqttv3.MqttCallback() {
            @Override
            public void connectionLost(Throwable cause) {}

            @Override
            public void messageArrived(String topic, org.eclipse.paho.client.mqttv3.MqttMessage message) {
                commands.add(message.getPayload());
            }

            @Override
            public void deliveryComplete(org.eclipse.paho.client.mqttv3.IMqttDeliveryToken token) {}
        });
        edge.connect();
        edge.subscribe(SET_TOPIC, 1);

        // edge báo state (revision 2) qua broker thật: backend học revision hiện tại từ đây
        String state = ContractExamples.text(ContractExamples.validBytes("state__normal.json"))
                .replaceAll("\"settings_revision\":\\s*\\d+", "\"settings_revision\": 2");
        edge.publish(STATE_TOPIC, state.getBytes(), 0, false);
        await().atMost(Duration.ofSeconds(10)).until(() -> live.get("edge01").isPresent());

        var view = settings.submit(
                new SettingsRequest(new BigDecimal("2.5"), 4, new BigDecimal("30"), 2, new BigDecimal("5")), "manager1");
        assertThat(view.status()).isEqualTo("PENDING");

        await().atMost(Duration.ofSeconds(10)).until(() -> !commands.isEmpty());
        JsonNode command = JSON.readTree(commands.get(0));
        assertThat(command.get("request_id").asText()).isEqualTo(view.requestId().toString());
        assertThat(command.get("expected_settings_revision").asInt()).isEqualTo(2);
        assertThat(command.get("dwell_seconds").asDouble()).isEqualTo(2.5);
        assertThat(command.get("on_count").asInt()).isEqualTo(4);

        // edge trả lời APPLIED (revision 3) qua broker
        String result = ContractExamples.text(ContractExamples.validBytes("settings-result__applied.json"))
                .replace("0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d", view.requestId().toString())
                .replaceAll("\"settings_revision\":\\s*\\d+", "\"settings_revision\": 3");
        edge.publish(RESULT_TOPIC, result.getBytes(), 1, false);
        await().atMost(Duration.ofSeconds(10)).untilAsserted(() ->
                assertThat(jdbc.queryForObject("select status from settings_revision", String.class)).isEqualTo("APPLIED"));
        assertThat(jdbc.queryForObject("select applied_revision from settings_revision", Integer.class)).isEqualTo(3);

        edge.disconnect();
        edge.close();
    }
}
