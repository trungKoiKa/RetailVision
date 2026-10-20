package vn.retailvision.dto.mqtt;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.UUID;

/** edge01/events/crossing */
public record CrossingMessage(
        @NotNull @Min(1) @Max(1) Integer schemaVersion,
        @NotNull UUID eventId,
        @NotBlank @Size(max = 64) String siteId,
        @NotBlank @Size(max = 64) String deviceId,
        @NotNull UUID sessionId,
        @NotNull @PositiveOrZero Long seq,
        @NotNull Instant occurredAt,
        @NotBlank @Size(max = 64) String configVersion,
        @NotNull @Pattern(regexp = "IN|OUT") String direction,
        @NotNull @PositiveOrZero Integer trackId,
        @NotBlank @Size(max = 32) String lineId,
        @NotNull @Pattern(regexp = "pilot|demo") String profile)
        implements EnvelopeMessage {}
