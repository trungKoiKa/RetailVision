package vn.retailvision.dto.request;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/** Ngưỡng vận hành sửa được từ web. Khoảng giá trị khớp contracts/mqtt/commands/settings-set.schema.json. */
public record SettingsRequest(
        @NotNull @DecimalMin("0") @DecimalMax("60") BigDecimal dwellSeconds,
        @NotNull @Min(1) @Max(100) Integer onCount,
        @NotNull @DecimalMin("0") @DecimalMax("3600") BigDecimal onHoldSeconds,
        @NotNull @Min(0) @Max(100) Integer offCount,
        @NotNull @DecimalMin("0") @DecimalMax("3600") BigDecimal offHoldSeconds) {}
