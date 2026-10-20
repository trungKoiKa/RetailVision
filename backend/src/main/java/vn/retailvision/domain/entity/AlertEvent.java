package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** Một dòng mỗi cảnh báo, gộp từ các transition OPEN/ACK/END. */
@Entity
@Table(name = "alert_event")
public class AlertEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "alert_id", nullable = false, unique = true)
    private UUID alertId;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(name = "opened_at", nullable = false)
    private Instant openedAt;

    @Column(name = "open_queue_count")
    private Integer openQueueCount;

    @Column(name = "acked_at")
    private Instant ackedAt;

    @Column(name = "ack_device_id")
    private String ackDeviceId;

    @Column(name = "ended_at")
    private Instant endedAt;

    @Column(name = "end_reason")
    private String endReason;

    protected AlertEvent() {}

    public UUID getAlertId() {
        return alertId;
    }

    public Instant getOpenedAt() {
        return openedAt;
    }

    public Integer getOpenQueueCount() {
        return openQueueCount;
    }

    public Instant getAckedAt() {
        return ackedAt;
    }

    public String getAckDeviceId() {
        return ackDeviceId;
    }

    public Instant getEndedAt() {
        return endedAt;
    }

    public String getEndReason() {
        return endReason;
    }
}
