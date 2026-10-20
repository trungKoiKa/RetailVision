package vn.retailvision.service.alert;

import java.time.Duration;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.domain.entity.AlertEvent;
import vn.retailvision.dto.response.AlertView;
import vn.retailvision.dto.response.PageResponse;
import vn.retailvision.repository.event.AlertEventRepository;

@Service
public class AlertQueryService {

    public static final int MAX_PAGE_SIZE = 100;

    private final AlertEventRepository alerts;

    public AlertQueryService(AlertEventRepository alerts) {
        this.alerts = alerts;
    }

    @Transactional(readOnly = true)
    public PageResponse<AlertView> list(int page, int size) {
        int safeSize = Math.min(Math.max(size, 1), MAX_PAGE_SIZE);
        Page<AlertEvent> result = alerts.findAllByOrderByOpenedAtDesc(PageRequest.of(Math.max(page, 0), safeSize));
        return new PageResponse<>(
                result.getContent().stream().map(AlertQueryService::toView).toList(),
                result.getNumber(),
                result.getSize(),
                result.getTotalElements());
    }

    @Transactional(readOnly = true)
    public Optional<AlertView> latest() {
        return alerts.findFirstByOrderByOpenedAtDesc().map(AlertQueryService::toView);
    }

    static AlertView toView(AlertEvent a) {
        Double latency = a.getAckedAt() == null
                ? null
                : Duration.between(a.getOpenedAt(), a.getAckedAt()).toMillis() / 1000.0;
        return new AlertView(
                a.getAlertId(),
                a.getOpenedAt(),
                a.getOpenQueueCount(),
                a.getAckedAt(),
                a.getAckDeviceId(),
                a.getEndedAt(),
                a.getEndReason(),
                a.getEndedAt() == null,
                latency);
    }
}
