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

/** Một yêu cầu đổi ngưỡng và kết quả edge trả về. */
@Entity
@Table(name = "settings_revision")
public class SettingsRevision {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "request_id", nullable = false, unique = true)
    private UUID requestId;

    @Column(name = "expected_revision", nullable = false)
    private int expectedRevision;

    @Column(name = "dwell_seconds", nullable = false)
    private BigDecimal dwellSeconds;

    @Column(name = "on_count", nullable = false)
    private int onCount;

    @Column(name = "on_hold_seconds", nullable = false)
    private BigDecimal onHoldSeconds;

    @Column(name = "off_count", nullable = false)
    private int offCount;

    @Column(name = "off_hold_seconds", nullable = false)
    private BigDecimal offHoldSeconds;

    @Column(nullable = false)
    private String status;

    private String reason;

    @Column(name = "applied_revision")
    private Integer appliedRevision;

    @Column(name = "requested_by", nullable = false)
    private String requestedBy;

    @Column(name = "requested_at", nullable = false)
    private Instant requestedAt;

    @Column(name = "resolved_at")
    private Instant resolvedAt;

    protected SettingsRevision() {}

    public SettingsRevision(
            UUID requestId,
            int expectedRevision,
            BigDecimal dwellSeconds,
            int onCount,
            BigDecimal onHoldSeconds,
            int offCount,
            BigDecimal offHoldSeconds,
            String requestedBy,
            Instant requestedAt) {
        this.requestId = requestId;
        this.expectedRevision = expectedRevision;
        this.dwellSeconds = dwellSeconds;
        this.onCount = onCount;
        this.onHoldSeconds = onHoldSeconds;
        this.offCount = offCount;
        this.offHoldSeconds = offHoldSeconds;
        this.status = "PENDING";
        this.requestedBy = requestedBy;
        this.requestedAt = requestedAt;
    }

    public UUID getRequestId() {
        return requestId;
    }

    public int getExpectedRevision() {
        return expectedRevision;
    }

    public BigDecimal getDwellSeconds() {
        return dwellSeconds;
    }

    public int getOnCount() {
        return onCount;
    }

    public BigDecimal getOnHoldSeconds() {
        return onHoldSeconds;
    }

    public int getOffCount() {
        return offCount;
    }

    public BigDecimal getOffHoldSeconds() {
        return offHoldSeconds;
    }

    public String getStatus() {
        return status;
    }

    public String getReason() {
        return reason;
    }

    public Integer getAppliedRevision() {
        return appliedRevision;
    }

    public String getRequestedBy() {
        return requestedBy;
    }

    public Instant getRequestedAt() {
        return requestedAt;
    }

    public Instant getResolvedAt() {
        return resolvedAt;
    }

    public void resolve(String status, Integer appliedRevision, String reason, Instant at) {
        this.status = status;
        this.appliedRevision = appliedRevision;
        this.reason = reason;
        this.resolvedAt = at;
    }
}
