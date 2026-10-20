package vn.retailvision.dto.response;

import java.time.Instant;
import java.util.UUID;

/** Một cảnh báo. ACK không đóng cảnh báo nên `open` chỉ phụ thuộc vào ended_at. */
public record AlertView(
        UUID alertId,
        Instant openedAt,
        Integer openQueueCount,
        Instant ackedAt,
        String ackDeviceId,
        Instant endedAt,
        String endReason,
        boolean open,
        Double ackLatencySeconds) {}
