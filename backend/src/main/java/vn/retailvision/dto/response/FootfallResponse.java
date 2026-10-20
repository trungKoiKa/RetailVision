package vn.retailvision.dto.response;

import java.time.LocalDate;
import java.util.List;

public record FootfallResponse(
        LocalDate from, LocalDate to, String granularity, String timezone, List<FootfallBucket> buckets, Totals totals) {

    /** Tổng chỉ cộng các bucket có số liệu; `gapBuckets` cho biết có bao nhiêu bucket thiếu dữ liệu. */
    public record Totals(long in, long out, int gapBuckets, Double coverage) {}
}
