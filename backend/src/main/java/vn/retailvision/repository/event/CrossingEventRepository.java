package vn.retailvision.repository.event;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.CrossingEvent;

public interface CrossingEventRepository extends JpaRepository<CrossingEvent, Long> {

    /** Trả 1 nếu ghi mới, 0 nếu event_id đã có (bản tin QoS 1 giao trùng). */
    @Modifying
    @Query(nativeQuery = true, value = """
            insert into crossing_event
                (event_id, session_id, seq, direction, line_id, track_id, profile, occurred_at)
            values (:eventId, :sessionId, :seq, :direction, :lineId, :trackId, :profile, :occurredAt)
            on conflict (event_id) do nothing
            """)
    int insertIgnore(
            @Param("eventId") UUID eventId,
            @Param("sessionId") UUID sessionId,
            @Param("seq") long seq,
            @Param("direction") String direction,
            @Param("lineId") String lineId,
            @Param("trackId") int trackId,
            @Param("profile") String profile,
            @Param("occurredAt") Instant occurredAt);

    @Query("select count(c) from CrossingEvent c where c.direction = :direction"
            + " and c.occurredAt >= :from and c.occurredAt < :to")
    long countBetween(
            @Param("direction") String direction, @Param("from") Instant from, @Param("to") Instant to);

    @Query("select c.profile from CrossingEvent c order by c.occurredAt desc limit 1")
    Optional<String> latestProfile();
}
