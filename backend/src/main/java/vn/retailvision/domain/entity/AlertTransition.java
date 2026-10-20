package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** Mọi bản tin transition nhận được (đã chống trùng theo event_id). Ghi bằng native insert. */
@Entity
@Table(name = "alert_transition")
public class AlertTransition {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_id", nullable = false, unique = true)
    private UUID eventId;

    @Column(name = "alert_id", nullable = false)
    private UUID alertId;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(nullable = false)
    private long seq;

    @Column(nullable = false)
    private String transition;

    @Column(name = "ack_id")
    private UUID ackId;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "server_received_at", nullable = false)
    private Instant serverReceivedAt;

    protected AlertTransition() {}

    public UUID getAlertId() {
        return alertId;
    }

    public String getTransition() {
        return transition;
    }
}
