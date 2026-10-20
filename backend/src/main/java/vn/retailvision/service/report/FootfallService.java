package vn.retailvision.service.report;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.Timestamp;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.List;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.dto.response.FootfallBucket;
import vn.retailvision.dto.response.FootfallResponse;
import vn.retailvision.exception.ApiException;

/**
 * Báo cáo lượt vào/ra theo giờ hoặc ngày kèm độ phủ quan sát. Nguyên tắc: thiếu dữ liệu là gap, không phải 0.
 * Mốc giờ/ngày tính theo múi giờ cấu hình (Asia/Ho_Chi_Minh), dữ liệu lưu UTC.
 */
@Service
public class FootfallService {

    public static final int MAX_HOUR_RANGE_DAYS = 7;
    public static final int MAX_DAY_RANGE_DAYS = 366;

    private static final String SQL = """
            with b as (
                select (g at time zone :zone) as s,
                       ((g + cast(:step as interval)) at time zone :zone) as e
                from generate_series(cast(:from as timestamp), cast(:toExclusive as timestamp) - cast(:step as interval),
                                     cast(:step as interval)) g
            )
            select b.s, b.e,
                (select count(*) from crossing_event c
                  where c.direction = 'IN' and c.occurred_at >= b.s and c.occurred_at < b.e) as in_count,
                (select count(*) from crossing_event c
                  where c.direction = 'OUT' and c.occurred_at >= b.s and c.occurred_at < b.e) as out_count,
                coalesce((select sum(t.valid_seconds) from telemetry_minute t
                           where t.minute_start >= b.s and t.minute_start < b.e), 0) as valid_seconds,
                (select sum(t.queue_avg * t.valid_seconds) filter (where t.queue_avg is not null)
                        / nullif(sum(t.valid_seconds) filter (where t.queue_avg is not null), 0)
                   from telemetry_minute t where t.minute_start >= b.s and t.minute_start < b.e) as queue_avg,
                (select max(t.queue_max) from telemetry_minute t
                  where t.minute_start >= b.s and t.minute_start < b.e) as queue_max,
                (select count(*) from alert_event a where a.opened_at >= b.s and a.opened_at < b.e) as alerts_opened,
                coalesce((select sum(extract(epoch from (least(coalesce(a.ended_at, :now), b.e) - greatest(a.opened_at, b.s))) / 60.0)
                            from alert_event a
                           where a.opened_at < b.e and coalesce(a.ended_at, :now) > b.s
                             and least(coalesce(a.ended_at, :now), b.e) > greatest(a.opened_at, b.s)), 0) as overload_minutes
            from b order by b.s
            """;

    private final NamedParameterJdbcTemplate jdbc;
    private final Clock clock;
    private final ZoneId zone;

    public FootfallService(NamedParameterJdbcTemplate jdbc, Clock clock, RetailVisionProperties props) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.zone = props.timezone();
    }

    public static LocalDate parseDate(String text, String field) {
        try {
            return LocalDate.parse(text);
        } catch (DateTimeParseException | NullPointerException e) {
            throw ApiException.badRequest(field + " phải có dạng yyyy-MM-dd");
        }
    }

    @Transactional(readOnly = true)
    public FootfallResponse report(LocalDate from, LocalDate to, String granularity) {
        boolean hourly = switch (granularity) {
            case "hour" -> true;
            case "day" -> false;
            default -> throw ApiException.badRequest("granularity phải là hour hoặc day");
        };
        if (to.isBefore(from)) {
            throw ApiException.badRequest("from không được sau to");
        }
        long days = ChronoUnit.DAYS.between(from, to) + 1;
        int limit = hourly ? MAX_HOUR_RANGE_DAYS : MAX_DAY_RANGE_DAYS;
        if (days > limit) {
            throw ApiException.badRequest("Khoảng quá dài: tối đa " + limit + " ngày khi gom theo " + (hourly ? "giờ" : "ngày"));
        }
        Instant now = clock.instant();
        var params = new MapSqlParameterSource()
                .addValue("zone", zone.getId())
                .addValue("step", hourly ? "1 hour" : "1 day")
                .addValue("from", Timestamp.valueOf(from.atStartOfDay()))
                .addValue("toExclusive", Timestamp.valueOf(to.plusDays(1).atStartOfDay()))
                .addValue("now", Timestamp.from(now));

        List<FootfallBucket> buckets = jdbc.query(SQL, params, (rs, i) -> {
            Instant start = rs.getTimestamp("s").toInstant();
            Instant end = rs.getTimestamp("e").toInstant();
            long in = rs.getLong("in_count");
            long out = rs.getLong("out_count");
            int valid = rs.getInt("valid_seconds");
            boolean future = !start.isBefore(now);
            long expected = future ? 0 : Math.max(0, Duration.between(start, end.isBefore(now) ? end : now).getSeconds());
            boolean gap = !future && valid == 0;
            boolean noData = gap && in == 0 && out == 0;
            Double coverage = future || expected == 0 ? null : Math.min(1.0, valid / (double) expected);
            BigDecimal avg = rs.getBigDecimal("queue_avg");
            int max = rs.getInt("queue_max");
            boolean maxNull = rs.wasNull();
            return new FootfallBucket(
                    start,
                    end,
                    future || noData ? null : in,
                    future || noData ? null : out,
                    valid,
                    expected,
                    coverage,
                    gap,
                    future,
                    rs.getInt("alerts_opened"),
                    Math.round(rs.getDouble("overload_minutes") * 10.0) / 10.0,
                    avg == null ? null : avg.setScale(2, RoundingMode.HALF_UP).doubleValue(),
                    maxNull ? null : max);
        });

        long totalIn = 0;
        long totalOut = 0;
        int gaps = 0;
        long valid = 0;
        long expected = 0;
        for (FootfallBucket b : buckets) {
            totalIn += b.in() == null ? 0 : b.in();
            totalOut += b.out() == null ? 0 : b.out();
            gaps += b.gap() ? 1 : 0;
            valid += b.validSeconds();
            expected += b.expectedSeconds();
        }
        Double overall = expected == 0 ? null : Math.min(1.0, valid / (double) expected);
        return new FootfallResponse(from, to, granularity, zone.getId(), buckets,
                new FootfallResponse.Totals(totalIn, totalOut, gaps, overall));
    }
}
