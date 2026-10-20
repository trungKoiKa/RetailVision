package vn.retailvision.controller.dashboard;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.response.OverviewResponse;
import vn.retailvision.service.report.OverviewService;

@RestController
@RequestMapping("/api/overview")
public class OverviewController {

    private final OverviewService overview;

    public OverviewController(OverviewService overview) {
        this.overview = overview;
    }

    @GetMapping
    public OverviewResponse get() {
        return overview.overview();
    }
}
