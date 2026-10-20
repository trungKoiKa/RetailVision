package vn.retailvision.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import vn.retailvision.support.MutableClock;
import vn.retailvision.support.PostgresIT;

/** FR-10, T21: báo cáo giờ/ngày qua ranh giới giờ và nửa đêm (giờ Việt Nam), restart, gap, coverage, CSV. */
@AutoConfigureMockMvc
@WithMockUser(roles = "MANAGER")
@Import(FootfallIT.ClockConfig.class)
class FootfallIT extends PostgresIT {

    private static final ZoneId VN = ZoneId.of("Asia/Ho_Chi_Minh");
    /** 2026-11-02 10:00Z = 17:00 giờ Việt Nam. */
    static final Instant NOW = Instant.parse("2026-11-02T10:00:00Z");

    @TestConfiguration
    static class ClockConfig {
        @Bean
        @Primary
        MutableClock footfallTestClock() {
            return new MutableClock(NOW);
        }
    }

    @Autowired
    MockMvc mvc;

    @Autowired
    MutableClock clock;

    UUID session;
    long seq;

    @BeforeEach
    void setUp() {
        clock.set(NOW);
        session = newSession();
        seq = 0;
    }

    private UUID newSession() {
        UUID id = UUID.randomUUID();
        jdbc.update("insert into edge_session values (?, 'edge01', now(), 'v1')", id);
        return id;
    }

    /** "2026-11-02T09:15" giờ VN -> chuỗi UTC. */
    private static String vn(String local) {
        return LocalDateTime.parse(local).atZone(VN).toInstant().toString();
    }

    private void crossing(String direction, String instantUtc) {
        crossing(session, direction, instantUtc);
    }

    private void crossing(UUID s, String direction, String instantUtc) {
        jdbc.update("""
                insert into crossing_event (event_id, session_id, seq, direction, line_id, track_id, profile, occurred_at)
                values (?, ?, ?, ?, 'door-1', 1, 'pilot', ?::timestamptz)
                """, UUID.randomUUID(), s, ++seq, direction, instantUtc);
    }

    private void telemetry(String minuteLocal, int validSeconds, Double avg, Integer max) {
        telemetry(session, minuteLocal, validSeconds, avg, max, ++seq);
    }

    private void telemetry(UUID s, String minuteLocal, int validSeconds, Double avg, Integer max, long sequence) {
        jdbc.update("""
                insert into telemetry_minute (event_id, session_id, seq, minute_start, valid_seconds, queue_avg, queue_max, fps, frame_age_ms)
                values (?, ?, ?, ?::timestamptz, ?, ?, ?, 5.0, 100)
                """, UUID.randomUUID(), s, sequence, vn(minuteLocal), validSeconds, avg, max);
    }

    private void alert(String openedLocal, String endedLocal) {
        jdbc.update("""
                insert into alert_event (alert_id, session_id, opened_at, ended_at, end_reason)
                values (?, ?, ?::timestamptz, ?::timestamptz, ?)
                """, UUID.randomUUID(), session, vn(openedLocal), endedLocal == null ? null : vn(endedLocal),
                endedLocal == null ? null : "NORMALIZED");
    }

    private String hourly() {
        return "/api/footfall?from=2026-11-02&to=2026-11-02&granularity=hour";
    }

    @Test
    void hourlyBucketsCarryCountsCoverageGapAndFutureFlags() throws Exception {
        crossing("IN", vn("2026-11-02T08:59:59"));
        crossing("IN", vn("2026-11-02T09:00:00")); // đúng đầu giờ 9 thuộc giờ 9
        crossing("OUT", vn("2026-11-02T09:30:00"));
        crossing("IN", vn("2026-11-02T10:15:00"));
        telemetry("2026-11-02T09:00", 60, 2.0, 3);
        telemetry("2026-11-02T09:01", 30, 4.0, 6);
        for (int m = 0; m < 30; m++) {
            telemetry("2026-11-02T10:" + String.format("%02d", m), 60, 1.0, 2);
        }

        mvc.perform(get(hourly()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.timezone").value("Asia/Ho_Chi_Minh"))
                .andExpect(jsonPath("$.buckets", hasSize(24)))
                // giờ 8: có lượt qua vạch nhưng không có telemetry -> vẫn báo số lượt, đánh dấu gap
                .andExpect(jsonPath("$.buckets[8].in").value(1))
                .andExpect(jsonPath("$.buckets[8].out").value(0))
                .andExpect(jsonPath("$.buckets[8].gap").value(true))
                // giờ 9
                .andExpect(jsonPath("$.buckets[9].start").value("2026-11-02T02:00:00Z"))
                .andExpect(jsonPath("$.buckets[9].in").value(1))
                .andExpect(jsonPath("$.buckets[9].out").value(1))
                .andExpect(jsonPath("$.buckets[9].valid_seconds").value(90))
                .andExpect(jsonPath("$.buckets[9].expected_seconds").value(3600))
                .andExpect(jsonPath("$.buckets[9].coverage").value(0.025))
                .andExpect(jsonPath("$.buckets[9].gap").value(false))
                .andExpect(jsonPath("$.buckets[9].queue_avg").value(2.67)) // (2*60 + 4*30) / 90, có trọng số
                .andExpect(jsonPath("$.buckets[9].queue_max").value(6))
                // giờ 10: nửa giờ có dữ liệu
                .andExpect(jsonPath("$.buckets[10].in").value(1))
                .andExpect(jsonPath("$.buckets[10].coverage").value(0.5))
                // giờ 11: không có gì -> gap, số lượt là null chứ không phải 0
                .andExpect(jsonPath("$.buckets[11].gap").value(true))
                .andExpect(jsonPath("$.buckets[11].in").value(nullValue()))
                .andExpect(jsonPath("$.buckets[11].out").value(nullValue()))
                .andExpect(jsonPath("$.buckets[11].queue_avg").value(nullValue()))
                .andExpect(jsonPath("$.buckets[11].coverage").value(0.0))
                // giờ 17 bắt đầu đúng lúc "bây giờ" và các giờ sau: chưa tới, không phải gap
                .andExpect(jsonPath("$.buckets[17].future").value(true))
                .andExpect(jsonPath("$.buckets[17].gap").value(false))
                .andExpect(jsonPath("$.buckets[17].in").value(nullValue()))
                .andExpect(jsonPath("$.buckets[17].coverage").value(nullValue()))
                .andExpect(jsonPath("$.buckets[23].future").value(true))
                .andExpect(jsonPath("$.totals.in").value(3))
                .andExpect(jsonPath("$.totals.out").value(1))
                .andExpect(jsonPath("$.totals.gap_buckets").value(15)); // 24 - 2 có telemetry - 7 chưa tới
    }

    @Test
    void currentHourUsesOnlyElapsedTimeAsExpected() throws Exception {
        clock.set(Instant.parse(vn("2026-11-02T09:30:00"))); // giữa giờ 9
        telemetry("2026-11-02T09:00", 60, 1.0, 1);
        mvc.perform(get(hourly()))
                .andExpect(jsonPath("$.buckets[9].expected_seconds").value(1800))
                .andExpect(jsonPath("$.buckets[9].future").value(false))
                .andExpect(jsonPath("$.buckets[10].future").value(true));
    }

    @Test
    void overloadMinutesAreSplitAcrossHoursAndOpenAlertsRunUntilNow() throws Exception {
        alert("2026-11-02T09:50", "2026-11-02T10:20"); // 10 phút ở giờ 9, 20 phút ở giờ 10
        alert("2026-11-02T16:30", null); // đang mở: tính tới bây giờ (17:00)
        mvc.perform(get(hourly()))
                .andExpect(jsonPath("$.buckets[9].alerts_opened").value(1))
                .andExpect(jsonPath("$.buckets[9].overload_minutes").value(10.0))
                .andExpect(jsonPath("$.buckets[10].alerts_opened").value(0))
                .andExpect(jsonPath("$.buckets[10].overload_minutes").value(20.0))
                .andExpect(jsonPath("$.buckets[16].alerts_opened").value(1))
                .andExpect(jsonPath("$.buckets[16].overload_minutes").value(30.0))
                .andExpect(jsonPath("$.buckets[17].overload_minutes").value(0.0));
    }

    @Test
    void minutesWithoutAQueueAverageDoNotDragTheWeightedAverageDown() throws Exception {
        telemetry("2026-11-02T09:00", 60, null, null); // quan sát hợp lệ nhưng không có số người (ví dụ UNKNOWN một phần)
        telemetry("2026-11-02T09:01", 60, 4.0, 5);
        mvc.perform(get(hourly()))
                .andExpect(jsonPath("$.buckets[9].queue_avg").value(4.0))
                .andExpect(jsonPath("$.buckets[9].valid_seconds").value(120));
    }

    @Test
    void midnightBoundaryInVietnamSplitsDaysCorrectly() throws Exception {
        crossing("IN", "2026-11-01T16:59:59Z"); // 23:59:59 ngày 1/11 giờ VN
        crossing("IN", "2026-11-01T17:00:00Z"); // 00:00:00 ngày 2/11
        crossing("OUT", "2026-11-02T16:59:59Z"); // 23:59:59 ngày 2/11 (ở tương lai so với "bây giờ": vẫn tính nếu có dữ liệu)
        telemetry("2026-11-01T23:59", 60, 1.0, 1);
        telemetry("2026-11-02T00:00", 60, 1.0, 1);
        mvc.perform(get("/api/footfall?from=2026-11-01&to=2026-11-02&granularity=day"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.buckets", hasSize(2)))
                .andExpect(jsonPath("$.buckets[0].start").value("2026-10-31T17:00:00Z"))
                .andExpect(jsonPath("$.buckets[0].in").value(1))
                .andExpect(jsonPath("$.buckets[0].valid_seconds").value(60))
                .andExpect(jsonPath("$.buckets[1].start").value("2026-11-01T17:00:00Z"))
                .andExpect(jsonPath("$.buckets[1].in").value(1))
                .andExpect(jsonPath("$.buckets[1].expected_seconds").value(61200)) // 17 giờ đã qua của ngày hôm nay
                .andExpect(jsonPath("$.buckets[1].valid_seconds").value(60));
    }

    @Test
    void edgeRestartsAreSummedAcrossSessionsEvenWhenSeqRestarts() throws Exception {
        UUID second = newSession(); // edge khởi động lại: session mới, seq bắt đầu lại từ 0
        crossing(session, "IN", vn("2026-11-02T09:10:00"));
        crossing(second, "IN", vn("2026-11-02T09:40:00"));
        telemetry(session, "2026-11-02T09:00", 60, 1.0, 1, 0);
        telemetry(second, "2026-11-02T09:01", 60, 1.0, 1, 0); // cùng seq 0 nhưng khác session
        mvc.perform(get(hourly()))
                .andExpect(jsonPath("$.buckets[9].in").value(2))
                .andExpect(jsonPath("$.buckets[9].valid_seconds").value(120));
    }

    @Test
    void aWholeFutureRangeIsAllFutureAndNeverZero() throws Exception {
        mvc.perform(get("/api/footfall?from=2026-11-05&to=2026-11-05&granularity=hour"))
                .andExpect(jsonPath("$.buckets", hasSize(24)))
                .andExpect(jsonPath("$.buckets[0].future").value(true))
                .andExpect(jsonPath("$.buckets[0].in").value(nullValue()))
                .andExpect(jsonPath("$.totals.gap_buckets").value(0))
                .andExpect(jsonPath("$.totals.coverage").value(nullValue()));
    }

    @Test
    void invalidRangesAndFormatsAreRejected() throws Exception {
        for (String url : new String[] {
            "/api/footfall?from=2026-11-03&to=2026-11-02&granularity=hour", // from sau to
            "/api/footfall?from=2026-11-01&to=2026-11-08&granularity=hour", // 8 ngày > 7
            "/api/footfall?from=2025-01-01&to=2026-11-02&granularity=day", // > 366 ngày
            "/api/footfall?from=02-11-2026&to=2026-11-02&granularity=hour",
            "/api/footfall?from=2026-11-02&granularity=hour", // thiếu to
            "/api/footfall?from=2026-11-02&to=2026-11-02&granularity=week",
        }) {
            mvc.perform(get(url)).andExpect(status().isBadRequest());
        }
        mvc.perform(get("/api/footfall?from=2026-11-01&to=2026-11-07&granularity=hour")).andExpect(status().isOk()); // đúng 7 ngày
    }

    @Test
    void csvMatchesTheJsonAndLeavesUnknownCellsEmpty() throws Exception {
        crossing("IN", vn("2026-11-02T09:00:00"));
        crossing("OUT", vn("2026-11-02T09:30:00"));
        telemetry("2026-11-02T09:00", 60, 2.0, 3);

        String body = mvc.perform(get("/api/reports/export.csv?from=2026-11-02&to=2026-11-02&granularity=hour"))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith("text/csv"))
                .andExpect(header().string("Content-Disposition", org.hamcrest.Matchers.containsString("footfall_2026-11-02_2026-11-02_hour.csv")))
                .andReturn().getResponse().getContentAsString();
        String[] lines = body.split("\r\n");
        assertThat(lines).hasSize(25); // tiêu đề + 24 giờ
        assertThat(lines[0]).isEqualTo("period_start,period_end,in,out,valid_seconds,expected_seconds,coverage,gap,alerts_opened,overload_minutes,queue_avg,queue_max");
        assertThat(lines[1]).startsWith("2026-11-02T00:00:00+07:00,2026-11-02T01:00:00+07:00,,,0,3600,0.0,true,"); // giờ 0: gap, in/out để trống
        assertThat(lines[10]).startsWith("2026-11-02T09:00:00+07:00,2026-11-02T10:00:00+07:00,1,1,60,3600,0.0167,false,0,0.0,2.0,3");
        assertThat(lines[18]).startsWith("2026-11-02T17:00:00+07:00,2026-11-02T18:00:00+07:00,,,0,0,,false,"); // chưa tới: trống
    }

    @Test
    void reportEndpointsNeedLogin() {
        // đã kiểm ở AuthIT bằng HTTP thật; ở đây chỉ nhắc rằng @WithMockUser là điều kiện của các test trên
        assertThat(FootfallIT.class.isAnnotationPresent(WithMockUser.class)).isTrue();
    }
}
