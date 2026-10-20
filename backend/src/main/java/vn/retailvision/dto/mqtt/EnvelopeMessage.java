package vn.retailvision.dto.mqtt;

import java.time.Instant;
import java.util.UUID;

/** Trường chung của mọi bản tin sự kiện (contracts/mqtt/common/envelope.schema.json). */
public interface EnvelopeMessage {
    Integer schemaVersion();

    UUID eventId();

    String siteId();

    String deviceId();

    UUID sessionId();

    Long seq();

    Instant occurredAt();

    String configVersion();
}
