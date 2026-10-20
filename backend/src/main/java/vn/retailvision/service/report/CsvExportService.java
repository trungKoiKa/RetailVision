package vn.retailvision.service.report;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import org.springframework.stereotype.Service;
import vn.retailvision.dto.response.FootfallBucket;
import vn.retailvision.dto.response.FootfallResponse;

/** CSV cùng số liệu với /api/footfall. Ô không có dữ liệu để trống (không điền 0). */
@Service
public class CsvExportService {

    static final String HEADER =
            "period_start,period_end,in,out,valid_seconds,expected_seconds,coverage,gap,alerts_opened,overload_minutes,queue_avg,queue_max";
    private static final DateTimeFormatter LOCAL = DateTimeFormatter.ISO_OFFSET_DATE_TIME;

    public String toCsv(FootfallResponse report) {
        ZoneId zone = ZoneId.of(report.timezone());
        StringBuilder sb = new StringBuilder(HEADER).append("\r\n");
        for (FootfallBucket b : report.buckets()) {
            sb.append(local(b.start(), zone)).append(',')
                    .append(local(b.end(), zone)).append(',')
                    .append(cell(b.in())).append(',')
                    .append(cell(b.out())).append(',')
                    .append(b.validSeconds()).append(',')
                    .append(b.expectedSeconds()).append(',')
                    .append(cell(b.coverage() == null ? null : round(b.coverage(), 4))).append(',')
                    .append(b.gap()).append(',')
                    .append(b.alertsOpened()).append(',')
                    .append(b.overloadMinutes()).append(',')
                    .append(cell(b.queueAvg())).append(',')
                    .append(cell(b.queueMax()))
                    .append("\r\n");
        }
        return sb.toString();
    }

    public String filename(FootfallResponse r) {
        return "footfall_" + r.from() + "_" + r.to() + "_" + r.granularity() + ".csv";
    }

    private static String local(Instant instant, ZoneId zone) {
        return LOCAL.format(instant.atZone(zone));
    }

    private static String cell(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private static double round(double v, int digits) {
        double f = Math.pow(10, digits);
        return Math.round(v * f) / f;
    }
}
