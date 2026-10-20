package vn.retailvision.service.device;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.domain.entity.DeviceStatus;
import vn.retailvision.dto.response.DeviceView;
import vn.retailvision.repository.monitoring.DeviceStatusRepository;
import vn.retailvision.service.queue.LiveStateCache;

@Service
public class DeviceQueryService {

    private final DeviceStatusRepository statuses;
    private final LiveStateCache live;
    private final RetailVisionProperties.Mqtt mqtt;

    public DeviceQueryService(DeviceStatusRepository statuses, LiveStateCache live, RetailVisionProperties props) {
        this.statuses = statuses;
        this.live = live;
        this.mqtt = props.mqtt();
    }

    /** edge01 và node01 luôn có mặt; thiết bị chưa từng báo là UNKNOWN. */
    @Transactional(readOnly = true)
    public List<DeviceView> devices() {
        Map<String, DeviceStatus> byId =
                statuses.findAll().stream().collect(Collectors.toMap(DeviceStatus::getDeviceId, Function.identity()));
        List<DeviceView> out = new ArrayList<>();
        for (String id : List.of(mqtt.edgeId(), mqtt.nodeId())) {
            DeviceStatus s = byId.get(id);
            Instant lastSeen = s == null ? null : s.getLastSeenAt();
            // edge phát state mỗi giây: lần nhận state cuối cũng là bằng chứng nó còn sống
            Instant stateSeen = live.get(id).map(LiveStateCache.Snapshot::receivedAt).orElse(null);
            if (stateSeen != null && (lastSeen == null || stateSeen.isAfter(lastSeen))) {
                lastSeen = stateSeen;
            }
            out.add(s == null
                    ? new DeviceView(id, "UNKNOWN", null, null, lastSeen)
                    : new DeviceView(id, s.getStatus(), s.getVersion(), s.isClockSynced(), lastSeen));
        }
        return out;
    }
}
