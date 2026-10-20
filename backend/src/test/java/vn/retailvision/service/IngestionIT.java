package vn.retailvision.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import vn.retailvision.exception.InvalidPayloadException;
import vn.retailvision.mqtt.MqttRouter;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.PostgresIT;

/** Ghi bản tin thật (ví dụ trong contracts) qua router vào PostgreSQL thật. Gồm T15: chống trùng event_id. */
class IngestionIT extends PostgresIT {

    private static final String P = "retailvision/v1/site01/";
    private static final String ALERT_ID = "5b8e2f10-1c3d-4e5f-8a6b-7c8d9e0f1a2b";

    @Autowired
    MqttRouter router;

    private void send(String topicSuffix, String example) {
        router.handle(P + topicSuffix, ContractExamples.validBytes(example));
    }

    @Test
    void t15_duplicateCrossingWithSameEventIdIsStoredOnce() {
        send("edge01/events/crossing", "crossing__in.json");
        send("edge01/events/crossing", "crossing__in.json"); // QoS 1 giao lại
        send("edge01/events/crossing", "crossing__in.json");

        assertThat(count("crossing_event")).isEqualTo(1);
        assertThat(count("edge_session")).isEqualTo(1);
    }

    @Test
    void crossingFieldsAreStoredAndTimeIsUtc() {
        send("edge01/events/crossing", "crossing__in.json");
        Map<String, Object> row = jdbc.queryForMap("select direction, line_id, track_id, profile, "
                + "to_char(occurred_at at time zone 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MS') as at from crossing_event");
        assertThat(row.get("direction")).isEqualTo("IN");
        assertThat(row.get("line_id")).isEqualTo("door-1");
        assertThat(row.get("track_id")).isEqualTo(17);
        assertThat(row.get("at")).isEqualTo("2026-11-02T10:05:11.400");
    }

    @Test
    void alertOpenAckEndBuildOneRowAndKeepEveryTransition() {
        send("edge01/events/alert", "alert__open.json");
        send("edge01/events/alert", "alert__ack.json");
        send("edge01/events/alert", "alert__end_normalized.json");

        assertThat(count("alert_transition")).isEqualTo(3);
        assertThat(count("alert_event")).isEqualTo(1);
        Map<String, Object> row = jdbc.queryForMap("select * from alert_event where alert_id = ?::uuid", ALERT_ID);
        assertThat(row.get("acked_at")).isNotNull();
        assertThat(row.get("ack_device_id")).isEqualTo("node01");
        assertThat(row.get("ended_at")).isNotNull();
        assertThat(row.get("end_reason")).isEqualTo("NORMALIZED");
        assertThat(row.get("open_queue_count")).isEqualTo(5);
    }

    @Test
    void duplicateAlertTransitionsDoNotChangeTheAlertRow() {
        send("edge01/events/alert", "alert__open.json");
        send("edge01/events/alert", "alert__open.json");
        send("edge01/events/alert", "alert__ack.json");
        send("edge01/events/alert", "alert__ack.json");

        assertThat(count("alert_transition")).isEqualTo(2);
        assertThat(count("alert_event")).isEqualTo(1);
    }

    @Test
    void ackAndEndArrivingBeforeOpenAreStillMergedIntoOneAlert() {
        send("edge01/events/alert", "alert__ack.json");
        send("edge01/events/alert", "alert__end_normalized.json");
        send("edge01/events/alert", "alert__open.json"); // đến muộn

        assertThat(count("alert_event")).isEqualTo(1);
        Map<String, Object> row = jdbc.queryForMap("select * from alert_event");
        assertThat(row.get("acked_at")).isNotNull();
        assertThat(row.get("ended_at")).isNotNull();
        assertThat(row.get("open_queue_count")).isEqualTo(5); // OPEN muộn vẫn ghi đè opened_at và số người
        assertThat(((java.sql.Timestamp) row.get("opened_at")).toInstant())
                .isBefore(((java.sql.Timestamp) row.get("acked_at")).toInstant());
    }

    @Test
    void telemetryDuplicateByEventIdIsIgnored() {
        send("edge01/telemetry", "telemetry__minute.json");
        send("edge01/telemetry", "telemetry__minute.json");
        assertThat(count("telemetry_minute")).isEqualTo(1);
        Map<String, Object> row = jdbc.queryForMap("select valid_seconds, queue_max from telemetry_minute");
        assertThat(row.get("valid_seconds")).isEqualTo(58);
    }

    @Test
    void stateIsNeverWrittenToTheDatabase() {
        send("edge01/state", "state__overload.json");
        send("edge01/state", "state__normal.json");
        send("edge01/state", "state__unknown.json");
        assertThat(count("crossing_event")).isZero();
        assertThat(count("alert_event")).isZero();
        assertThat(count("telemetry_minute")).isZero();
        assertThat(count("edge_session")).isZero();
    }

    @Test
    void statusUpsertsLatestPerDeviceInArrivalOrder() {
        send("edge01/status", "status__online.json");
        assertThat(jdbc.queryForObject("select status from device_status where device_id = 'edge01'", String.class))
                .isEqualTo("ONLINE");
        // Last Will tới sau: có occurred_at cũ hơn nhưng phải thắng vì đến sau
        byte[] offline = ContractExamples.text(ContractExamples.validBytes("status__online.json"))
                .replace("\"ONLINE\"", "\"OFFLINE\"")
                .replace("2026-11-02T10:00:00.000Z", "2026-11-02T09:00:00.000Z")
                .getBytes();
        router.handle(P + "edge01/status", offline);
        assertThat(jdbc.queryForObject("select status from device_status where device_id = 'edge01'", String.class))
                .isEqualTo("OFFLINE");
        assertThat(count("device_status")).isEqualTo(1);
    }

    @Test
    void messageClaimingAnotherDeviceOrSiteIsRejectedAndNotStored() {
        String forgedDevice = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"))
                .replace("\"edge01\"", "\"edge99\"");
        assertThatThrownBy(() -> router.handle(P + "edge01/events/crossing", forgedDevice.getBytes()))
                .isInstanceOf(InvalidPayloadException.class);
        String forgedSite = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"))
                .replace("\"site01\"", "\"site02\"");
        assertThatThrownBy(() -> router.handle(P + "edge01/events/crossing", forgedSite.getBytes()))
                .isInstanceOf(InvalidPayloadException.class);
        assertThat(count("crossing_event")).isZero();
    }

    @Test
    void unknownTopicIsRejected() {
        assertThatThrownBy(() -> router.handle(P + "edge01/events/other", new byte[] {'{', '}'}))
                .isInstanceOf(InvalidPayloadException.class);
        assertThatThrownBy(() -> router.handle("other/prefix/state", new byte[] {'{', '}'}))
                .isInstanceOf(InvalidPayloadException.class);
    }
}
