package vn.retailvision.repository.event;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.AlertEvent;

/**
 * Mỗi transition được gộp vào một dòng alert_event. Các câu upsert chịu được bản tin đến sai thứ tự:
 * ACK hoặc END đến trước OPEN thì tạo dòng tạm, OPEN đến sau sẽ ghi đè opened_at và số người.
 */
public interface AlertEventRepository extends JpaRepository<AlertEvent, Long> {

    @Modifying
    @Query(nativeQuery = true, value = """
            insert into alert_event (alert_id, session_id, opened_at, open_queue_count)
            values (:alertId, :sessionId, :at, :queueCount)
            on conflict (alert_id) do update
                set opened_at = excluded.opened_at, open_queue_count = excluded.open_queue_count
            """)
    int upsertOpen(
            @Param("alertId") UUID alertId,
            @Param("sessionId") UUID sessionId,
            @Param("at") Instant at,
            @Param("queueCount") Integer queueCount);

    @Modifying
    @Query(nativeQuery = true, value = """
            insert into alert_event (alert_id, session_id, opened_at, acked_at, ack_device_id)
            values (:alertId, :sessionId, :at, :at, :deviceId)
            on conflict (alert_id) do update
                set acked_at = coalesce(alert_event.acked_at, excluded.acked_at),
                    ack_device_id = coalesce(alert_event.ack_device_id, excluded.ack_device_id)
            """)
    int upsertAck(
            @Param("alertId") UUID alertId,
            @Param("sessionId") UUID sessionId,
            @Param("at") Instant at,
            @Param("deviceId") String deviceId);

    @Modifying
    @Query(nativeQuery = true, value = """
            insert into alert_event (alert_id, session_id, opened_at, ended_at, end_reason)
            values (:alertId, :sessionId, :at, :at, :reason)
            on conflict (alert_id) do update
                set ended_at = coalesce(alert_event.ended_at, excluded.ended_at),
                    end_reason = coalesce(alert_event.end_reason, excluded.end_reason)
            """)
    int upsertEnd(
            @Param("alertId") UUID alertId,
            @Param("sessionId") UUID sessionId,
            @Param("at") Instant at,
            @Param("reason") String reason);

    Page<AlertEvent> findAllByOrderByOpenedAtDesc(Pageable pageable);

    Optional<AlertEvent> findFirstByOrderByOpenedAtDesc();

    Optional<AlertEvent> findByAlertId(UUID alertId);
}
