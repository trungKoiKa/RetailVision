package vn.retailvision.domain.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** Trạng thái mới nhất của một thiết bị theo topic status (retained). */
@Entity
@Table(name = "device_status")
public class DeviceStatus {

    @Id
    @Column(name = "device_id")
    private String deviceId;

    @Column(name = "site_id", nullable = false)
    private String siteId;

    @Column(nullable = false)
    private String status;

    @Column(nullable = false)
    private String version;

    @Column(name = "clock_synced", nullable = false)
    private boolean clockSynced;

    @Column(name = "reported_at", nullable = false)
    private Instant reportedAt;

    @Column(name = "last_seen_at", nullable = false)
    private Instant lastSeenAt;

    protected DeviceStatus() {}

    public String getDeviceId() {
        return deviceId;
    }

    public String getStatus() {
        return status;
    }

    public String getVersion() {
        return version;
    }

    public boolean isClockSynced() {
        return clockSynced;
    }

    public Instant getReportedAt() {
        return reportedAt;
    }

    public Instant getLastSeenAt() {
        return lastSeenAt;
    }
}
