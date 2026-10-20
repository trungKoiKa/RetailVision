package vn.retailvision.controller.report;

import java.nio.charset.StandardCharsets;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.response.FootfallResponse;
import vn.retailvision.service.report.CsvExportService;
import vn.retailvision.service.report.FootfallService;

@RestController
@RequestMapping("/api/reports")
public class ReportController {

    private final FootfallService footfall;
    private final CsvExportService csv;

    public ReportController(FootfallService footfall, CsvExportService csv) {
        this.footfall = footfall;
        this.csv = csv;
    }

    @GetMapping("/export.csv")
    public ResponseEntity<byte[]> export(
            @RequestParam String from,
            @RequestParam String to,
            @RequestParam(defaultValue = "hour") String granularity) {
        FootfallResponse report =
                footfall.report(FootfallService.parseDate(from, "from"), FootfallService.parseDate(to, "to"), granularity);
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "csv", StandardCharsets.UTF_8))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        ContentDisposition.attachment().filename(csv.filename(report)).build().toString())
                .body(csv.toCsv(report).getBytes(StandardCharsets.UTF_8));
    }
}
