package vn.retailvision.controller.footfall;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.response.FootfallResponse;
import vn.retailvision.service.report.FootfallService;

@RestController
@RequestMapping("/api/footfall")
public class FootfallController {

    private final FootfallService footfall;

    public FootfallController(FootfallService footfall) {
        this.footfall = footfall;
    }

    /** from/to là ngày theo giờ Việt Nam (yyyy-MM-dd, gồm cả hai đầu). */
    @GetMapping
    public FootfallResponse get(
            @RequestParam String from,
            @RequestParam String to,
            @RequestParam(defaultValue = "hour") String granularity) {
        return footfall.report(FootfallService.parseDate(from, "from"), FootfallService.parseDate(to, "to"), granularity);
    }
}
