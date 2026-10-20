package vn.retailvision.dto.mqtt;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.UUID;

/** edge01/telemetry: tổng hợp mỗi 60 giây, QoS 1. */
public record TelemetryMessage(
        @NotNull @Min(1) @Max(1) Integer schemaVersion,
        @NotNull UUID eventId,
        @NotBlank @Size(max = 64) String siteId,
        @NotBlank @Size(max = 64) String deviceId,
        @NotNull UUID sessionId,
        @NotNull @PositiveOrZero Long seq,
        @NotNull Instant occurredAt,
        @NotBlank @Size(max = 64) String configVersion,
        @NotNull Instant minuteStart,
        @NotNull @Min(0) @Max(60) Integer validSeconds,
        @DecimalMin("0") @DecimalMax("1000") BigDecimal queueAvg,
        @Min(0) @Max(1000) Integer queueMax,
        @NotNull @DecimalMin("0") BigDecimal fps,
        @NotNull @PositiveOrZero Integer frameAgeMs)
        implements EnvelopeMessage {

    @JsonIgnore
    @AssertTrue(message = "minute_start phải tròn phút")
    public boolean isMinuteStartAligned() {
        return minuteStart == null || minuteStart.atOffset(ZoneOffset.UTC).getSecond() == 0
                && minuteStart.getNano() == 0;
    }
}
