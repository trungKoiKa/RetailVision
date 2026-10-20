package vn.retailvision.repository.event;

import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.AlertTransition;

public interface AlertTransitionRepository extends JpaRepository<AlertTransition, Long> {

    @Modifying
    @Query(nativeQuery = true, value = """
            insert into alert_transition
                (event_id, alert_id, session_id, seq, transition, ack_id, occurred_at)
            values (:eventId, :alertId, :sessionId, :seq, :transition, :ackId, :occurredAt)
            on conflict (event_id) do nothing
            """)
    int insertIgnore(
            @Param("eventId") UUID eventId,
            @Param("alertId") UUID alertId,
            @Param("sessionId") UUID sessionId,
            @Param("seq") long seq,
            @Param("transition") String transition,
            @Param("ackId") UUID ackId,
            @Param("occurredAt") Instant occurredAt);
}
