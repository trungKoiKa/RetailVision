package vn.retailvision.dto.response;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class SettingsViews {

    private SettingsViews() {}

    public record Values(BigDecimal dwellSeconds, int onCount, BigDecimal onHoldSeconds, int offCount, BigDecimal offHoldSeconds) {}

    /**
     * Trạng thái một yêu cầu: PENDING (đang chờ edge), UNCONFIRMED (quá hạn chờ mà edge chưa trả lời; không coi là
     * đã áp dụng, kết quả đến muộn vẫn cập nhật), APPLIED, REJECTED (kèm lý do).
     */
    public record Request(
            UUID requestId,
            String status,
            String reason,
            int expectedRevision,
            Integer appliedRevision,
            Values values,
            String requestedBy,
            Instant requestedAt,
            Instant resolvedAt) {}

    /**
     * `edgeRevision` lấy từ state mới nhất của edge (null nếu không có dữ liệu mới). `current` là ngưỡng của lần
     * APPLIED gần nhất; null nghĩa là chưa từng đổi từ web (edge dùng giá trị trong file cấu hình của nó).
     */
    public record Overview(Integer edgeRevision, Values current, Request latest, List<Request> history, boolean canSubmit, String cannotSubmitReason) {}
}
