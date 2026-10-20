package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/** Telemetry mỗi phút. `validSeconds` là độ phủ quan sát; phút không có dòng là gap, không phải 0. */
@Entity
@Table(name = "telemetry_minute")
public class TelemetryMinute {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_id", nullable = false, unique = true)
    private UUID eventId;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(nullable = false)
    private long seq;

    @Column(name = "minute_start", nullable = false)
    private Instant minuteStart;

    @Column(name = "valid_seconds", nullable = false)
    private int validSeconds;

    @Column(name = "queue_avg")
    private BigDecimal queueAvg;

    @Column(name = "queue_max")
    private Integer queueMax;

    @Column(nullable = false)
    private BigDecimal fps;

    @Column(name = "frame_age_ms", nullable = false)
    private int frameAgeMs;

    @Column(name = "server_received_at", nullable = false)
    private Instant serverReceivedAt;

    protected TelemetryMinute() {}

    public Instant getMinuteStart() {
        return minuteStart;
    }

    public int getValidSeconds() {
        return validSeconds;
    }
}
