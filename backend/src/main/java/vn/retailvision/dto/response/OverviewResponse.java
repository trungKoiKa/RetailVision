package vn.retailvision.dto.response;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public record OverviewResponse(Today today, Live live, AlertView lastAlert, String profile, List<DeviceView> devices) {

    /** Số lượt trong ngày theo múi giờ cấu hình. */
    public record Today(LocalDate date, String timezone, long in, long out) {}

    /**
     * Trạng thái hiện tại. Chưa có state hoặc state cũ thì state = UNKNOWN, queueCount = null
     * (không phải 0) và stale = true.
     */
    public record Live(
            String state,
            Integer queueCount,
            UUID alertId,
            boolean acked,
            Instant observedAt,
            Double ageSeconds,
            boolean stale,
            String configVersion) {}
}
