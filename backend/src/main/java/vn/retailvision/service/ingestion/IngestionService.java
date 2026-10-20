package vn.retailvision.service.ingestion;

import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.dto.mqtt.AlertMessage;
import vn.retailvision.dto.mqtt.CrossingMessage;
import vn.retailvision.dto.mqtt.EnvelopeMessage;
import vn.retailvision.dto.mqtt.StatusMessage;
import vn.retailvision.dto.mqtt.TelemetryMessage;
import vn.retailvision.repository.event.AlertEventRepository;
import vn.retailvision.repository.event.AlertTransitionRepository;
import vn.retailvision.repository.event.CrossingEventRepository;
import vn.retailvision.repository.event.EdgeSessionRepository;
import vn.retailvision.repository.event.TelemetryMinuteRepository;
import vn.retailvision.repository.monitoring.DeviceStatusRepository;

/**
 * Ghi sự kiện từ MQTT vào PostgreSQL. Mỗi hàm là một transaction; chỉ khi hàm trả về (đã commit)
 * thì listener mới ack broker. Bản tin giao trùng bị chặn bằng ON CONFLICT trên event_id nên ghi lại
 * an toàn, không ném lỗi.
 */
@Service
public class IngestionService {

    private static final Logger log = LoggerFactory.getLogger(IngestionService.class);

    private final EdgeSessionRepository sessions;
    private final CrossingEventRepository crossings;
    private final AlertTransitionRepository transitions;
    private final AlertEventRepository alerts;
    private final TelemetryMinuteRepository telemetry;
    private final DeviceStatusRepository devices;
    private final Clock clock;

    public IngestionService(
            EdgeSessionRepository sessions,
            CrossingEventRepository crossings,
            AlertTransitionRepository transitions,
            AlertEventRepository alerts,
            TelemetryMinuteRepository telemetry,
            DeviceStatusRepository devices,
            Clock clock) {
        this.sessions = sessions;
        this.crossings = crossings;
        this.transitions = transitions;
        this.alerts = alerts;
        this.telemetry = telemetry;
        this.devices = devices;
        this.clock = clock;
    }

    /** @return true nếu là bản ghi mới, false nếu trùng event_id. */
    @Transactional
    public boolean ingest(CrossingMessage m) {
        ensureSession(m);
        int rows = crossings.insertIgnore(
                m.eventId(), m.sessionId(), m.seq(), m.direction(), m.lineId(), m.trackId(), m.profile(), m.occurredAt());
        return rows == 1;
    }

    /** @return true nếu là transition mới, false nếu trùng event_id. */
    @Transactional
    public boolean ingest(AlertMessage m) {
        ensureSession(m);
        int rows = transitions.insertIgnore(
                m.eventId(), m.alertId(), m.sessionId(), m.seq(), m.transition(), m.ackId(), m.occurredAt());
        if (rows == 0) {
            return false; // bản trùng: alert_event đã được cập nhật lần đầu
        }
        switch (m.transition()) {
            case "OPEN" -> alerts.upsertOpen(m.alertId(), m.sessionId(), m.occurredAt(), m.queueCount());
            case "ACK" -> alerts.upsertAck(m.alertId(), m.sessionId(), m.occurredAt(), m.ackDeviceId());
            case "END" -> alerts.upsertEnd(m.alertId(), m.sessionId(), m.occurredAt(), m.reason());
            default -> throw new IllegalStateException("transition không hỗ trợ: " + m.transition());
        }
        return true;
    }

    /** @return true nếu là telemetry mới, false nếu trùng event_id hoặc (session, seq). */
    @Transactional
    public boolean ingest(TelemetryMessage m) {
        ensureSession(m);
        int rows = telemetry.insertIgnore(
                m.eventId(), m.sessionId(), m.seq(), m.minuteStart(), m.validSeconds(),
                m.queueAvg(), m.queueMax(), m.fps(), m.frameAgeMs());
        return rows == 1;
    }

    /** Ghi trạng thái thiết bị mới nhất; idempotent theo device_id. */
    @Transactional
    public void ingest(StatusMessage m) {
        Instant now = clock.instant();
        devices.upsert(m.deviceId(), m.siteId(), m.status(), m.version(), m.clockSynced(), m.occurredAt(), now);
        log.info("Thiết bị {} báo {}", m.deviceId(), m.status());
    }

    private void ensureSession(EnvelopeMessage m) {
        UUID sessionId = m.sessionId();
        sessions.insertIgnore(sessionId, m.deviceId(), m.occurredAt(), m.configVersion());
    }
}
