package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "crossing_event")
public class CrossingEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "event_id", nullable = false, unique = true)
    private UUID eventId;

    @Column(name = "session_id", nullable = false)
    private UUID sessionId;

    @Column(nullable = false)
    private long seq;

    @Column(nullable = false)
    private String direction;

    @Column(name = "line_id", nullable = false)
    private String lineId;

    @Column(name = "track_id", nullable = false)
    private int trackId;

    @Column(nullable = false)
    private String profile;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    @Column(name = "server_received_at", nullable = false)
    private Instant serverReceivedAt;

    protected CrossingEvent() {}

    public Long getId() {
        return id;
    }

    public UUID getEventId() {
        return eventId;
    }

    public String getDirection() {
        return direction;
    }

    public String getProfile() {
        return profile;
    }

    public Instant getOccurredAt() {
        return occurredAt;
    }
}
