package vn.retailvision.controller.alert;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.response.AlertView;
import vn.retailvision.dto.response.PageResponse;
import vn.retailvision.service.alert.AlertQueryService;

@RestController
@Validated
@RequestMapping("/api/alerts")
public class AlertController {

    private final AlertQueryService alerts;

    public AlertController(AlertQueryService alerts) {
        this.alerts = alerts;
    }

    /** Cảnh báo mới nhất trước, phân trang. */
    @GetMapping
    public PageResponse<AlertView> list(
            @RequestParam(defaultValue = "0") @Min(0) int page,
            @RequestParam(defaultValue = "20") @Min(1) @Max(AlertQueryService.MAX_PAGE_SIZE) int size) {
        return alerts.list(page, size);
    }
}
