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

/** edge01/settings/result: edge trả lời lệnh settings/set. */
public record SettingsResultMessage(
        @NotNull @Min(1) @Max(1) Integer schemaVersion,
        @NotNull UUID eventId,
        @NotBlank @Size(max = 64) String siteId,
        @NotBlank @Size(max = 64) String deviceId,
        @NotNull UUID sessionId,
        @NotNull @PositiveOrZero Long seq,
        @NotNull Instant occurredAt,
        @NotBlank @Size(max = 64) String configVersion,
        @NotNull UUID requestId,
        @NotNull @Pattern(regexp = "APPLIED|REJECTED") String result,
        @NotNull @PositiveOrZero Integer settingsRevision,
        @Size(max = 200) String reason)
        implements EnvelopeMessage {}
