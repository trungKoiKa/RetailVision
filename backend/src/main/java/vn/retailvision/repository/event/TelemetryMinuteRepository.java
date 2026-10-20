package vn.retailvision.repository.event;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.TelemetryMinute;

public interface TelemetryMinuteRepository extends JpaRepository<TelemetryMinute, Long> {

    /** Bỏ qua khi trùng event_id hoặc trùng (session_id, seq). */
    @Modifying
    @Query(nativeQuery = true, value = """
            insert into telemetry_minute
                (event_id, session_id, seq, minute_start, valid_seconds, queue_avg, queue_max, fps, frame_age_ms)
            values (:eventId, :sessionId, :seq, :minuteStart, :validSeconds, :queueAvg, :queueMax, :fps, :frameAgeMs)
            on conflict do nothing
            """)
    int insertIgnore(
            @Param("eventId") UUID eventId,
            @Param("sessionId") UUID sessionId,
            @Param("seq") long seq,
            @Param("minuteStart") Instant minuteStart,
            @Param("validSeconds") int validSeconds,
            @Param("queueAvg") BigDecimal queueAvg,
            @Param("queueMax") Integer queueMax,
            @Param("fps") BigDecimal fps,
            @Param("frameAgeMs") int frameAgeMs);
}
