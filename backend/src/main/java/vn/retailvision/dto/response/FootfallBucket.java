package vn.retailvision.dto.response;

import java.time.Instant;

/**
 * Một giờ hoặc một ngày (theo múi giờ cấu hình).
 *
 * <p>`in`/`out` là null khi không có dữ liệu nào (không telemetry và không lượt qua vạch): đó là "không biết",
 * không phải 0. `gap` = đã qua hoặc đang diễn ra mà không có telemetry nào (độ phủ 0). `future` = chưa tới.
 * `coverage` = giây quan sát hợp lệ / giây đáng ra có (tối đa 1).
 */
public record FootfallBucket(
        Instant start,
        Instant end,
        Long in,
        Long out,
        int validSeconds,
        long expectedSeconds,
        Double coverage,
        boolean gap,
        boolean future,
        int alertsOpened,
        double overloadMinutes,
        Double queueAvg,
        Integer queueMax) {}
