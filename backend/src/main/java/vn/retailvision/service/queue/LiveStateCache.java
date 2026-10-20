package vn.retailvision.service.queue;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.dto.mqtt.StateMessage;

/**
 * State mới nhất của từng edge, giữ trong RAM (state là QoS 0 nên không vào DB).
 * Độ tươi tính theo giờ máy chủ lúc nhận, không tin đồng hồ của Pi.
 */
@Component
public class LiveStateCache {

    /** Ảnh chụp state kèm thời điểm nhận. */
    public record Snapshot(
            String state,
            Integer queueCount,
            UUID alertId,
            boolean acked,
            Instant observedAt,
            String configVersion,
            Instant receivedAt) {}

    private final Map<String, Snapshot> byDevice = new ConcurrentHashMap<>();
    private final Clock clock;
    private final Duration staleAfter;

    public LiveStateCache(Clock clock, RetailVisionProperties props) {
        this.clock = clock;
        this.staleAfter = Duration.ofSeconds(props.staleSeconds());
    }

    public void update(StateMessage m) {
        byDevice.put(
                m.deviceId(),
                new Snapshot(m.state(), m.queueCount(), m.alertId(), m.acked(), m.observedAt(), m.configVersion(), clock.instant()));
    }

    /** Xoá toàn bộ state đang giữ (dùng trong test để cô lập các ca). */
    public void clear() {
        byDevice.clear();
    }

    public Optional<Snapshot> get(String deviceId) {
        return Optional.ofNullable(byDevice.get(deviceId));
    }

    public boolean isStale(Snapshot snapshot) {
        return Duration.between(snapshot.receivedAt(), clock.instant()).compareTo(staleAfter) > 0;
    }

    public double ageSeconds(Snapshot snapshot) {
        return Duration.between(snapshot.receivedAt(), clock.instant()).toMillis() / 1000.0;
    }
}
