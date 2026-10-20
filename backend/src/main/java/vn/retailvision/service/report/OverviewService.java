package vn.retailvision.service.report;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.dto.response.OverviewResponse;
import vn.retailvision.repository.event.CrossingEventRepository;
import vn.retailvision.service.alert.AlertQueryService;
import vn.retailvision.service.device.DeviceQueryService;
import vn.retailvision.service.queue.LiveStateCache;

@Service
public class OverviewService {

    private final CrossingEventRepository crossings;
    private final AlertQueryService alerts;
    private final DeviceQueryService devices;
    private final LiveStateCache liveCache;
    private final Clock clock;
    private final ZoneId zone;
    private final String edgeId;

    public OverviewService(
            CrossingEventRepository crossings,
            AlertQueryService alerts,
            DeviceQueryService devices,
            LiveStateCache liveCache,
            Clock clock,
            RetailVisionProperties props) {
        this.crossings = crossings;
        this.alerts = alerts;
        this.devices = devices;
        this.liveCache = liveCache;
        this.clock = clock;
        this.zone = props.timezone();
        this.edgeId = props.mqtt().edgeId();
    }

    @Transactional(readOnly = true)
    public OverviewResponse overview() {
        LocalDate today = LocalDate.now(clock.withZone(zone));
        Instant from = today.atStartOfDay(zone).toInstant();
        Instant to = today.plusDays(1).atStartOfDay(zone).toInstant();
        var counts = new OverviewResponse.Today(
                today,
                zone.getId(),
                crossings.countBetween("IN", from, to),
                crossings.countBetween("OUT", from, to));
        return new OverviewResponse(
                counts,
                live(),
                alerts.latest().orElse(null),
                crossings.latestProfile().orElse(null),
                devices.devices());
    }

    private OverviewResponse.Live live() {
        var snapshot = liveCache.get(edgeId);
        if (snapshot.isEmpty()) {
            return new OverviewResponse.Live("UNKNOWN", null, null, false, null, null, true, null, null);
        }
        var s = snapshot.get();
        double age = liveCache.ageSeconds(s);
        if (liveCache.isStale(s)) {
            // dữ liệu cũ: không biết hiện tại, trả UNKNOWN và null (không phải 0)
            return new OverviewResponse.Live("UNKNOWN", null, null, false, s.observedAt(), age, true, s.configVersion(), s.settingsRevision());
        }
        return new OverviewResponse.Live(
                s.state(), s.queueCount(), s.alertId(), s.acked(), s.observedAt(), age, false, s.configVersion(), s.settingsRevision());
    }
}
