package vn.retailvision.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import vn.retailvision.exception.InvalidPayloadException;
import vn.retailvision.mqtt.MqttPublisher;
import vn.retailvision.mqtt.MqttRouter;
import vn.retailvision.service.queue.LiveStateCache;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MutableClock;
import vn.retailvision.support.PostgresIT;

/** FR-09 (P1), T15, T16: đổi ngưỡng từ web, PENDING tới khi edge xác nhận, revision cũ không ghi đè. */
@AutoConfigureMockMvc
@WithMockUser(username = "manager1", roles = "MANAGER")
@Import(SettingsIT.TestBeans.class)
class SettingsIT extends PostgresIT {

    static final Instant NOW = Instant.parse("2026-11-02T10:00:00Z");
    static final String P = "retailvision/v1/site01/";
    static final ObjectMapper JSON = new ObjectMapper();

    static class FakePublisher implements MqttPublisher {
        record Sent(String topic, byte[] payload, int qos, boolean retain) {}

        final List<Sent> sent = new ArrayList<>();
        boolean failNext;

        @Override
        public void publish(String topic, byte[] payload, int qos, boolean retain) {
            if (failNext) {
                failNext = false;
                throw new PublishFailedException("broker không trả lời", null);
            }
            sent.add(new Sent(topic, payload, qos, retain));
        }
    }

    @TestConfiguration
    static class TestBeans {
        @Bean
        @Primary
        MutableClock settingsTestClock() {
            return new MutableClock(NOW);
        }

        @Bean
        FakePublisher fakePublisher() {
            return new FakePublisher();
        }
    }

    @Autowired
    MockMvc mvc;

    @Autowired
    MutableClock clock;

    @Autowired
    FakePublisher publisher;

    @Autowired
    MqttRouter router;

    @Autowired
    LiveStateCache liveCache;

    @BeforeEach
    void setUp() {
        clock.set(NOW);
        publisher.sent.clear();
        publisher.failNext = false;
        liveCache.clear();
    }

    /** state từ ví dụ contract nhưng với revision tùy chọn. */
    private void edgeState(int revision) {
        String json = ContractExamples.text(ContractExamples.validBytes("state__normal.json"))
                .replaceAll("\"settings_revision\":\\s*\\d+", "\"settings_revision\": " + revision);
        router.handle(P + "edge01/state", json.getBytes());
    }

    private static String body(int dwell, int on, int onHold, int off, int offHold) {
        return String.format("{\"dwell_seconds\":%d,\"on_count\":%d,\"on_hold_seconds\":%d,\"off_count\":%d,\"off_hold_seconds\":%d}",
                dwell, on, onHold, off, offHold);
    }

    private ResultActions sendPut(String json) throws Exception {
        return mvc.perform(put("/api/settings").with(csrf()).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private String submit(String json) throws Exception {
        String response = sendPut(json).andExpect(status().isAccepted()).andReturn().getResponse().getContentAsString();
        return JSON.readTree(response).get("request_id").asText();
    }

    private void result(String requestId, String result, int revision, String reason) {
        String json = ContractExamples.text(ContractExamples.validBytes("settings-result__applied.json"))
                .replace("0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d", requestId)
                .replace("\"APPLIED\"", "\"" + result + "\"")
                .replaceAll("\"settings_revision\":\\s*\\d+", "\"settings_revision\": " + revision)
                .replace("\"reason\": null", reason == null ? "\"reason\": null" : "\"reason\": \"" + reason + "\"");
        router.handle(P + "edge01/settings/result", json.getBytes());
    }

    @Test
    void cannotSubmitWithoutFreshEdgeData() throws Exception {
        sendPut(body(2, 5, 60, 3, 10)).andExpect(status().isConflict());
        mvc.perform(get("/api/settings"))
                .andExpect(jsonPath("$.can_submit").value(false))
                .andExpect(jsonPath("$.edge_revision").value(nullValue()))
                .andExpect(jsonPath("$.current").value(nullValue()));
        assertThat(publisher.sent).isEmpty();

        edgeState(0);
        clock.advance(Duration.ofSeconds(6)); // state cũ quá 5 giây: không biết revision hiện tại
        sendPut(body(2, 5, 60, 3, 10)).andExpect(status().isConflict());
        assertThat(publisher.sent).isEmpty();
    }

    @Test
    void validRequestIsStoredPendingAndPublishedWithTheEdgeRevision() throws Exception {
        edgeState(4);
        sendPut(body(3, 4, 30, 2, 5))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.status").value("PENDING"))
                .andExpect(jsonPath("$.expected_revision").value(4))
                .andExpect(jsonPath("$.requested_by").value("manager1"));

        assertThat(count("settings_revision")).isEqualTo(1);
        assertThat(publisher.sent).hasSize(1);
        var sent = publisher.sent.get(0);
        assertThat(sent.topic()).isEqualTo(P + "edge01/settings/set");
        assertThat(sent.qos()).isEqualTo(1);
        assertThat(sent.retain()).isFalse();
        JsonNode payload = JSON.readTree(sent.payload());
        assertThat(payload.get("expected_settings_revision").asInt()).isEqualTo(4);
        assertThat(payload.get("on_count").asInt()).isEqualTo(4);
        assertThat(payload.get("dwell_seconds").isIntegralNumber()).isTrue();
        assertThat(payload.get("device_id").asText()).isEqualTo("edge01");
        assertPayloadMatchesContract(payload);
    }

    /** Khóa và kiểu của lệnh phải đúng settings-set.schema.json + envelope (không thừa, không thiếu). */
    private static void assertPayloadMatchesContract(JsonNode payload) throws Exception {
        Path root = Path.of("..", "contracts", "mqtt");
        JsonNode set = JSON.readTree(Files.readString(root.resolve("commands/settings-set.schema.json")));
        JsonNode envelope = JSON.readTree(Files.readString(root.resolve("common/envelope.schema.json")));
        Set<String> required = new HashSet<>();
        set.get("required").forEach(n -> required.add(n.asText()));
        envelope.get("required").forEach(n -> required.add(n.asText()));
        Set<String> actual = new HashSet<>();
        payload.fieldNames().forEachRemaining(actual::add);
        assertThat(actual).isEqualTo(required);
        assertThat(payload.get("schema_version").asInt()).isEqualTo(1);
        assertThat(UUID.fromString(payload.get("event_id").asText())).isNotNull();
        assertThat(UUID.fromString(payload.get("request_id").asText())).isNotNull();
        assertThat(payload.get("occurred_at").asText()).matches("\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{1,6})?Z");
        JsonNode props = set.get("properties");
        for (String field : new String[] {"dwell_seconds", "on_count", "on_hold_seconds", "off_count", "off_hold_seconds"}) {
            double v = payload.get(field).asDouble();
            assertThat(v).as(field).isBetween(props.get(field).get("minimum").asDouble(), props.get(field).get("maximum").asDouble());
        }
    }

    @Test
    void appliedResultMakesTheValuesCurrentAndKeepsTheRevision() throws Exception {
        edgeState(0);
        String id = submit(body(3, 4, 30, 2, 5));
        result(id, "APPLIED", 1, null);
        mvc.perform(get("/api/settings"))
                .andExpect(jsonPath("$.latest.status").value("APPLIED"))
                .andExpect(jsonPath("$.latest.applied_revision").value(1))
                .andExpect(jsonPath("$.current.on_count").value(4))
                .andExpect(jsonPath("$.current.dwell_seconds").value(3.0))
                .andExpect(jsonPath("$.can_submit").value(true));
    }

    @Test
    void rejectedResultKeepsTheReasonAndNeverBecomesCurrent() throws Exception {
        edgeState(0);
        String id = submit(body(3, 4, 30, 2, 5));
        result(id, "REJECTED", 0, "revision cũ: edge đang ở 2");
        mvc.perform(get("/api/settings"))
                .andExpect(jsonPath("$.latest.status").value("REJECTED"))
                .andExpect(jsonPath("$.latest.reason").value("revision cũ: edge đang ở 2"))
                .andExpect(jsonPath("$.current").value(nullValue()));
    }

    @Test
    void secondRequestWhilePendingIsRefusedAndNothingIsPublished() throws Exception {
        edgeState(0);
        submit(body(3, 4, 30, 2, 5));
        sendPut(body(2, 6, 60, 3, 10)).andExpect(status().isConflict());
        assertThat(publisher.sent).hasSize(1);
        assertThat(count("settings_revision")).isEqualTo(1);
    }

    @Test
    void unansweredRequestBecomesUnconfirmedNotAppliedAndAnLateAnswerStillResolvesIt() throws Exception {
        edgeState(0);
        String first = submit(body(3, 4, 30, 2, 5));
        clock.advance(Duration.ofSeconds(31));
        edgeState(0); // state mới để không bị coi là cũ
        mvc.perform(get("/api/settings"))
                .andExpect(jsonPath("$.latest.status").value("UNCONFIRMED"))
                .andExpect(jsonPath("$.current").value(nullValue())) // chưa xác nhận thì không phải ngưỡng hiện hành
                .andExpect(jsonPath("$.can_submit").value(true));
        String second = submit(body(2, 6, 60, 3, 10)); // được gửi lại
        assertThat(second).isNotEqualTo(first);

        result(first, "APPLIED", 1, null); // câu trả lời đến muộn cho yêu cầu đầu
        result(second, "REJECTED", 1, "revision cũ");
        mvc.perform(get("/api/settings"))
                .andExpect(jsonPath("$.history[1].status").value("APPLIED"))
                .andExpect(jsonPath("$.history[0].status").value("REJECTED"))
                .andExpect(jsonPath("$.current.on_count").value(4));
    }

    @Test
    void duplicateOrUnknownResultsAreHarmless() throws Exception {
        edgeState(0);
        String id = submit(body(3, 4, 30, 2, 5));
        result(id, "APPLIED", 1, null);
        result(id, "REJECTED", 1, "bản trùng muộn"); // kết quả đầu tiên thắng
        result(UUID.randomUUID().toString(), "APPLIED", 9, null); // request_id lạ
        mvc.perform(get("/api/settings")).andExpect(jsonPath("$.latest.status").value("APPLIED"));
        assertThat(count("settings_revision")).isEqualTo(1);
    }

    @Test
    void invalidValuesAreRejectedAndNothingIsStoredOrPublished() throws Exception {
        edgeState(0);
        String[] bad = {
            body(2, 0, 60, 0, 10), // on_count < 1
            body(2, 3, 60, 3, 10), // off_count >= on_count (T16)
            body(2, 3, 60, 4, 10),
            body(61, 5, 60, 3, 10), // dwell > 60
            body(-1, 5, 60, 3, 10),
            body(2, 101, 60, 3, 10),
            body(2, 5, 3601, 3, 10),
            "{\"dwell_seconds\":2,\"on_count\":5,\"on_hold_seconds\":60,\"off_count\":3}", // thiếu trường
            "{\"dwell_seconds\":\"hai\",\"on_count\":5,\"on_hold_seconds\":60,\"off_count\":3,\"off_hold_seconds\":10}",
            "{}",
            "khong phai json",
        };
        for (String json : bad) {
            sendPut(json).andExpect(status().isBadRequest());
        }
        assertThat(publisher.sent).isEmpty();
        assertThat(count("settings_revision")).isZero();
    }

    @Test
    void failureToPublishIsReportedAndRecordedAsRejected() throws Exception {
        edgeState(0);
        publisher.failNext = true;
        sendPut(body(3, 4, 30, 2, 5)).andExpect(status().isServiceUnavailable());
        assertThat(jdbc.queryForObject("select status from settings_revision", String.class)).isEqualTo("REJECTED");
        // không kẹt PENDING: gửi lại được ngay
        submit(body(3, 4, 30, 2, 5));
    }

    @Test
    void writesNeedCsrf() throws Exception {
        edgeState(0);
        mvc.perform(put("/api/settings").contentType(MediaType.APPLICATION_JSON).content(body(3, 4, 30, 2, 5)))
                .andExpect(status().isForbidden());
        assertThat(publisher.sent).isEmpty();
    }

    @Test
    void sequenceNumbersOfCommandsIncrease() throws Exception {
        edgeState(0);
        String a = submit(body(3, 4, 30, 2, 5));
        result(a, "APPLIED", 1, null);
        edgeState(1);
        submit(body(2, 6, 60, 3, 10));
        long s0 = JSON.readTree(publisher.sent.get(0).payload()).get("seq").asLong();
        long s1 = JSON.readTree(publisher.sent.get(1).payload()).get("seq").asLong();
        assertThat(s1).isGreaterThan(s0);
        assertThat(JSON.readTree(publisher.sent.get(1).payload()).get("expected_settings_revision").asInt()).isEqualTo(1);
    }

    @Test
    void malformedResultMessagesAreRejectedByTheParser() {
        String valid = ContractExamples.text(ContractExamples.validBytes("settings-result__applied.json"));
        for (String bad : new String[] {
            valid.replace("\"APPLIED\"", "\"MAYBE\""),
            valid.replace("\"request_id\"", "\"req\""),
            valid.replace("\"settings_revision\": 1", "\"settings_revision\": -1"),
            valid.replace("\"device_id\": \"edge01\"", "\"device_id\": \"edge99\""),
        }) {
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> router.handle(P + "edge01/settings/result", bad.getBytes()))
                    .isInstanceOf(InvalidPayloadException.class);
        }
    }

    @Test
    void overviewExposesTheEdgeSettingsRevision() throws Exception {
        edgeState(7);
        mvc.perform(get("/api/overview")).andExpect(jsonPath("$.live.settings_revision").value(7));
    }
}
