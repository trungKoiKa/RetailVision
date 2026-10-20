package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

/** Một lần chạy của edge. Ghi bằng native insert; entity có mặt để Hibernate kiểm khớp schema. */
@Entity
@Table(name = "edge_session")
public class EdgeSession {

    @Id
    @Column(name = "session_id")
    private UUID sessionId;

    @Column(name = "device_id", nullable = false)
    private String deviceId;

    @Column(name = "started_at", nullable = false)
    private Instant startedAt;

    @Column(name = "config_version", nullable = false)
    private String configVersion;

    protected EdgeSession() {}

    public UUID getSessionId() {
        return sessionId;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public String getConfigVersion() {
        return configVersion;
    }
}
