package vn.retailvision.controller;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.web.servlet.MockMvc;
import vn.retailvision.mqtt.MqttRouter;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MutableClock;
import vn.retailvision.support.PostgresIT;
import vn.retailvision.service.queue.LiveStateCache;

@AutoConfigureMockMvc
@Import(ApiIT.ClockConfig.class)
class ApiIT extends PostgresIT {

    /** 2026-11-02 10:00Z = 17:00 giờ Việt Nam. */
    static final Instant NOW = Instant.parse("2026-11-02T10:00:00Z");
    private static final String P = "retailvision/v1/site01/";

    @TestConfiguration
    static class ClockConfig {
        @Bean
        @Primary
        MutableClock testClock() {
            return new MutableClock(NOW);
        }
    }

    @Autowired
    MockMvc mvc;

    @Autowired
    MutableClock clock;

    @Autowired
    MqttRouter router;

    @Autowired
    LiveStateCache liveCache;

    @BeforeEach
    void resetClockAndCache() {
        clock.set(NOW);
        liveCache.clear();
    }

    private void state(String example) {
        router.handle(P + "edge01/state", ContractExamples.validBytes(example));
    }

    @Test
    void overviewWithoutAnyStateIsUnknownAndNeverZero() throws Exception {
        mvc.perform(get("/api/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.live.state").value("UNKNOWN"))
                .andExpect(jsonPath("$.live.queue_count").value(nullValue()))
                .andExpect(jsonPath("$.live.stale").value(true))
                .andExpect(jsonPath("$.last_alert").value(nullValue()))
                .andExpect(jsonPath("$.devices[?(@.device_id == 'edge01')].status").value("UNKNOWN"))
                .andExpect(jsonPath("$.devices[?(@.device_id == 'node01')].status").value("UNKNOWN"));
    }

    @Test
    void overviewShowsFreshOverloadState() throws Exception {
        state("state__overload.json");
        mvc.perform(get("/api/overview"))
                .andExpect(jsonPath("$.live.state").value("OVERLOAD"))
                .andExpect(jsonPath("$.live.queue_count").value(5))
                .andExpect(jsonPath("$.live.acked").value(false))
                .andExpect(jsonPath("$.live.stale").value(false))
                .andExpect(jsonPath("$.live.age_seconds").value(0.0));
    }

    @Test
    void staleStateTurnsIntoUnknownWithNullCountNotTheLastValue() throws Exception {
        state("state__overload.json");
        clock.advance(Duration.ofSeconds(6)); // quá stale-seconds = 5
        mvc.perform(get("/api/overview"))
                .andExpect(jsonPath("$.live.state").value("UNKNOWN"))
                .andExpect(jsonPath("$.live.queue_count").value(nullValue()))
                .andExpect(jsonPath("$.live.alert_id").value(nullValue()))
                .andExpect(jsonPath("$.live.stale").value(true))
                .andExpect(jsonPath("$.live.age_seconds").value(6.0));
    }

    @Test
    void unknownStateFromEdgeKeepsCountNull() throws Exception {
        state("state__unknown.json");
        mvc.perform(get("/api/overview"))
                .andExpect(jsonPath("$.live.state").value("UNKNOWN"))
                .andExpect(jsonPath("$.live.queue_count").value(nullValue()))
                .andExpect(jsonPath("$.live.stale").value(false));
    }

    @Test
    void todayCountsFollowTheVietnamDayBoundaries() throws Exception {
        UUID session = UUID.randomUUID();
        jdbc.update("insert into edge_session values (?, 'edge01', now(), 'v1')", session);
        // ngày 2026-11-02 giờ VN = [2026-11-01T17:00Z, 2026-11-02T17:00Z)
        insertCrossing(session, "IN", "2026-11-01T16:59:59Z"); // hôm trước (23:59:59 ngày 1)
        insertCrossing(session, "IN", "2026-11-01T17:00:00Z"); // 00:00:00 hôm nay
        insertCrossing(session, "OUT", "2026-11-02T16:59:59Z"); // 23:59:59 hôm nay
        insertCrossing(session, "OUT", "2026-11-02T17:00:00Z"); // 00:00:00 ngày mai
        mvc.perform(get("/api/overview"))
                .andExpect(jsonPath("$.today.date").value("2026-11-02"))
                .andExpect(jsonPath("$.today.timezone").value("Asia/Ho_Chi_Minh"))
                .andExpect(jsonPath("$.today.in").value(1))
                .andExpect(jsonPath("$.today.out").value(1));
    }

    private void insertCrossing(UUID session, String direction, String at) {
        jdbc.update("""
                insert into crossing_event (event_id, session_id, seq, direction, line_id, track_id, profile, occurred_at)
                values (?, ?, 1, ?, 'door-1', 1, 'pilot', ?::timestamptz)
                """, UUID.randomUUID(), session, direction, at);
    }

    @Test
    void alertsArePagedNewestFirstWithAckLatencyAndOpenFlag() throws Exception {
        UUID session = UUID.randomUUID();
        jdbc.update("insert into edge_session values (?, 'edge01', now(), 'v1')", session);
        insertAlert(session, "2026-11-02T08:00:00Z", "2026-11-02T08:00:12Z", "2026-11-02T08:05:00Z"); // cũ nhất
        insertAlert(session, "2026-11-02T09:00:00Z", null, "2026-11-02T09:03:00Z"); // chưa ACK
        insertAlert(session, "2026-11-02T09:50:00Z", "2026-11-02T09:50:30Z", null); // đang mở, đã ACK

        mvc.perform(get("/api/alerts").param("page", "0").param("size", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.total").value(3))
                .andExpect(jsonPath("$.items", hasSize(2)))
                .andExpect(jsonPath("$.items[0].opened_at").value("2026-11-02T09:50:00Z"))
                .andExpect(jsonPath("$.items[0].open").value(true))
                .andExpect(jsonPath("$.items[0].ack_latency_seconds").value(30.0))
                .andExpect(jsonPath("$.items[1].acked_at").value(nullValue()))
                .andExpect(jsonPath("$.items[1].ack_latency_seconds").value(nullValue()))
                .andExpect(jsonPath("$.items[1].open").value(false));
        mvc.perform(get("/api/alerts").param("page", "1").param("size", "2"))
                .andExpect(jsonPath("$.items", hasSize(1)))
                .andExpect(jsonPath("$.items[0].ack_latency_seconds").value(12.0));
        mvc.perform(get("/api/overview"))
                .andExpect(jsonPath("$.last_alert.opened_at").value("2026-11-02T09:50:00Z"));
    }

    private void insertAlert(UUID session, String opened, String acked, String ended) {
        jdbc.update("""
                insert into alert_event (alert_id, session_id, opened_at, acked_at, ack_device_id, ended_at, end_reason)
                values (?, ?, ?::timestamptz, ?::timestamptz, ?, ?::timestamptz, ?)
                """, UUID.randomUUID(), session, opened, acked, acked == null ? null : "node01", ended,
                ended == null ? null : "NORMALIZED");
    }

    @Test
    void invalidPagingParametersAreRejected() throws Exception {
        mvc.perform(get("/api/alerts").param("size", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/alerts").param("size", "101")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/alerts").param("page", "-1")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/alerts").param("page", "abc")).andExpect(status().isBadRequest());
    }

    @Test
    void devicesListBothDevicesAndReflectReportedStatus() throws Exception {
        router.handle(P + "edge01/status", ContractExamples.validBytes("status__online.json"));
        mvc.perform(get("/api/devices"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].device_id").value("edge01"))
                .andExpect(jsonPath("$[0].status").value("ONLINE"))
                .andExpect(jsonPath("$[0].clock_synced").value(true))
                .andExpect(jsonPath("$[1].device_id").value("node01"))
                .andExpect(jsonPath("$[1].status").value("UNKNOWN"));
    }

    @Test
    void healthReportsDatabaseUpAndMqttDisabledInThisTest() throws Exception {
        mvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("UP"))
                .andExpect(jsonPath("$.database").value(true))
                .andExpect(jsonPath("$.mqtt.enabled").value(false));
    }
}
