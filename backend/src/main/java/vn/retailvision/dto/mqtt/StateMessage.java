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

/** edge01/state: snapshot 1 Hz, QoS 0. Chỉ cập nhật bộ nhớ, không vào DB. */
public record StateMessage(
        @NotNull @Min(1) @Max(1) Integer schemaVersion,
        @NotNull UUID eventId,
        @NotBlank @Size(max = 64) String siteId,
        @NotBlank @Size(max = 64) String deviceId,
        @NotNull UUID sessionId,
        @NotNull @PositiveOrZero Long seq,
        @NotNull Instant occurredAt,
        @NotBlank @Size(max = 64) String configVersion,
        @NotNull Instant observedAt,
        @NotNull @Pattern(regexp = "NORMAL|OVERLOAD|UNKNOWN") String state,
        @Min(0) @Max(1000) Integer queueCount,
        UUID alertId,
        @NotNull Boolean acked,
        @NotNull @PositiveOrZero Integer settingsRevision)
        implements EnvelopeMessage {

    @JsonIgnore
    @AssertTrue(message = "UNKNOWN không được có queue_count")
    public boolean isUnknownHasNoCount() {
        return !"UNKNOWN".equals(state) || queueCount == null;
    }
}
