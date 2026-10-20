package vn.retailvision.service.settings;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.domain.entity.SettingsRevision;
import vn.retailvision.dto.mqtt.SettingsResultMessage;
import vn.retailvision.dto.request.SettingsRequest;
import vn.retailvision.dto.response.SettingsViews;
import vn.retailvision.exception.ApiException;
import vn.retailvision.mqtt.MqttPublisher;
import vn.retailvision.repository.settings.SettingsRevisionRepository;
import vn.retailvision.service.queue.LiveStateCache;

/**
 * Đổi ngưỡng từ web (FR-09, P1): lưu yêu cầu PENDING, gửi settings/set kèm revision edge đang có, giữ PENDING
 * cho tới khi edge trả APPLIED/REJECTED. Quá hạn chờ thì hiện "chưa xác nhận", không coi là đã áp dụng.
 * Backend không tự quyết định ngưỡng có hiệu lực: chỉ edge xác nhận.
 */
@Service
public class SettingsService {

    private static final Logger log = LoggerFactory.getLogger(SettingsService.class);

    private final SettingsRevisionRepository repository;
    private final LiveStateCache live;
    private final ObjectProvider<MqttPublisher> publisher;
    private final Clock clock;
    private final RetailVisionProperties props;
    private final Duration timeout;
    private final TransactionTemplate tx;
    private final UUID sessionId = UUID.randomUUID();
    private final AtomicLong seq = new AtomicLong();
    private final ObjectMapper json = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
            .build();

    public SettingsService(
            SettingsRevisionRepository repository,
            LiveStateCache live,
            ObjectProvider<MqttPublisher> publisher,
            Clock clock,
            RetailVisionProperties props,
            PlatformTransactionManager transactionManager) {
        this.tx = new TransactionTemplate(transactionManager);
        this.repository = repository;
        this.live = live;
        this.publisher = publisher;
        this.clock = clock;
        this.props = props;
        this.timeout = Duration.ofSeconds(props.settingsTimeoutSeconds());
    }

    // --- đọc ------------------------------------------------------------

    @Transactional(readOnly = true)
    public SettingsViews.Overview overview() {
        Integer revision = freshEdgeRevision().orElse(null);
        List<SettingsViews.Request> history = repository.findTop10ByOrderByRequestedAtDesc().stream().map(this::view).toList();
        SettingsViews.Values current = repository.findFirstByStatusOrderByAppliedRevisionDesc("APPLIED")
                .map(SettingsService::values).orElse(null);
        String blocked = blockedReason(revision);
        return new SettingsViews.Overview(revision, current, history.isEmpty() ? null : history.get(0), history, blocked == null, blocked);
    }

    // --- gửi ------------------------------------------------------------

    public SettingsViews.Request submit(SettingsRequest request, String username) {
        List<String> problems = problems(request);
        if (!problems.isEmpty()) {
            throw ApiException.badRequest(String.join("; ", problems));
        }
        MqttPublisher mqtt = publisher.getIfAvailable();
        if (mqtt == null) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "MQTT_DISABLED", "Backend chưa bật MQTT nên không gửi được lệnh");
        }
        Integer revision = freshEdgeRevision().orElse(null);
        String blocked = blockedReason(revision);
        if (blocked != null) {
            throw ApiException.conflict(blocked);
        }

        SettingsRevision saved = save(request, revision, username);
        try {
            mqtt.publish(props.mqtt().topicPrefix() + props.mqtt().edgeId() + "/settings/set", payload(saved), 1, false);
        } catch (MqttPublisher.PublishFailedException e) {
            resolve(saved.getRequestId(), "REJECTED", null, "Backend không gửi được lệnh tới broker: " + e.getMessage());
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "MQTT_UNAVAILABLE", "Không gửi được lệnh tới broker MQTT");
        }
        return view(saved);
    }

    /** Ghi yêu cầu PENDING và commit trước khi gửi, để kết quả đến rất nhanh vẫn tìm thấy dòng này. */
    private SettingsRevision save(SettingsRequest r, int expectedRevision, String username) {
        return tx.execute(status -> repository.saveAndFlush(new SettingsRevision(
                UUID.randomUUID(), expectedRevision, r.dwellSeconds(), r.onCount(), r.onHoldSeconds(), r.offCount(),
                r.offHoldSeconds(), username, clock.instant())));
    }

    // --- nhận kết quả -----------------------------------------------------

    /** Edge trả lời. Idempotent: kết quả trùng không ghi đè; request_id lạ bị bỏ qua. */
    @Transactional
    public void onResult(SettingsResultMessage m) {
        Optional<SettingsRevision> found = repository.findByRequestId(m.requestId());
        if (found.isEmpty()) {
            log.warn("settings/result cho request_id không biết: {}", m.requestId());
            return;
        }
        SettingsRevision row = found.get();
        if (!"PENDING".equals(row.getStatus())) {
            return; // đã có kết quả: bản trùng
        }
        row.resolve(m.result(), m.settingsRevision(), m.reason(), clock.instant());
        log.info("Edge {} yêu cầu đổi ngưỡng {} (revision {})", m.result(), m.requestId(), m.settingsRevision());
    }

    private void resolve(UUID requestId, String status, Integer revision, String reason) {
        tx.executeWithoutResult(t -> repository.findByRequestId(requestId)
                .ifPresent(r -> r.resolve(status, revision, reason, clock.instant())));
    }

    // --- nội bộ ---------------------------------------------------------

    private Optional<Integer> freshEdgeRevision() {
        return live.get(props.mqtt().edgeId())
                .filter(s -> !live.isStale(s))
                .map(LiveStateCache.Snapshot::settingsRevision);
    }

    private String blockedReason(Integer revision) {
        if (revision == null) {
            return "Edge không có dữ liệu mới nên không thể đổi ngưỡng lúc này";
        }
        Optional<SettingsRevision> pending = repository.findFirstByStatusOrderByRequestedAtDesc("PENDING");
        if (pending.isPresent() && !expired(pending.get())) {
            return "Đang chờ edge xác nhận yêu cầu trước";
        }
        return null;
    }

    private boolean expired(SettingsRevision r) {
        return clock.instant().isAfter(r.getRequestedAt().plus(timeout));
    }

    private SettingsViews.Request view(SettingsRevision r) {
        String status = "PENDING".equals(r.getStatus()) && expired(r) ? "UNCONFIRMED" : r.getStatus();
        return new SettingsViews.Request(r.getRequestId(), status, r.getReason(), r.getExpectedRevision(),
                r.getAppliedRevision(), values(r), r.getRequestedBy(), r.getRequestedAt(), r.getResolvedAt());
    }

    private static SettingsViews.Values values(SettingsRevision r) {
        return new SettingsViews.Values(r.getDwellSeconds(), r.getOnCount(), r.getOnHoldSeconds(), r.getOffCount(), r.getOffHoldSeconds());
    }

    /** Kiểm các quy tắc chéo mà annotation không diễn đạt được. */
    static List<String> problems(SettingsRequest r) {
        if (r.onCount() != null && r.offCount() != null && r.offCount() >= r.onCount()) {
            return List.of("off_count phải nhỏ hơn on_count");
        }
        return List.of();
    }

    private byte[] payload(SettingsRevision r) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("schema_version", 1);
        body.put("event_id", UUID.randomUUID());
        body.put("site_id", props.mqtt().siteId());
        body.put("device_id", props.mqtt().edgeId());
        body.put("session_id", sessionId);
        body.put("seq", seq.getAndIncrement());
        body.put("occurred_at", clock.instant());
        body.put("config_version", "backend");
        body.put("request_id", r.getRequestId());
        body.put("expected_settings_revision", r.getExpectedRevision());
        body.put("dwell_seconds", number(r.getDwellSeconds()));
        body.put("on_count", r.getOnCount());
        body.put("on_hold_seconds", number(r.getOnHoldSeconds()));
        body.put("off_count", r.getOffCount());
        body.put("off_hold_seconds", number(r.getOffHoldSeconds()));
        try {
            return json.writeValueAsBytes(body);
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Số nguyên giữ nguyên dạng nguyên (2), số thập phân giữ nguyên (2.5). */
    private static Number number(BigDecimal v) {
        BigDecimal stripped = v.stripTrailingZeros();
        return stripped.scale() <= 0 ? (Number) stripped.longValueExact() : stripped.doubleValue();
    }
}
