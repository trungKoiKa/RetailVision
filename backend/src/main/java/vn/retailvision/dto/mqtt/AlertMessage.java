package vn.retailvision.dto.mqtt;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.UUID;

/** edge01/events/alert: transition OPEN / ACK / END. */
public record AlertMessage(
        @NotNull @Min(1) @Max(1) Integer schemaVersion,
        @NotNull UUID eventId,
        @NotBlank @Size(max = 64) String siteId,
        @NotBlank @Size(max = 64) String deviceId,
        @NotNull UUID sessionId,
        @NotNull @PositiveOrZero Long seq,
        @NotNull Instant occurredAt,
        @NotBlank @Size(max = 64) String configVersion,
        @NotNull UUID alertId,
        @NotNull @Pattern(regexp = "OPEN|ACK|END") String transition,
        @Min(0) @Max(1000) Integer queueCount,
        @Pattern(regexp = "NORMALIZED|INTERRUPTED|CONFIG_CHANGED") String reason,
        UUID ackId,
        @Size(min = 1, max = 64) String ackDeviceId)
        implements EnvelopeMessage {

    @JsonIgnore
    @AssertTrue(message = "END phải có reason")
    public boolean isEndHasReason() {
        return !"END".equals(transition) || reason != null;
    }

    @JsonIgnore
    @AssertTrue(message = "ACK phải có ack_id và ack_device_id")
    public boolean isAckHasIds() {
        return !"ACK".equals(transition) || (ackId != null && ackDeviceId != null);
    }
}
