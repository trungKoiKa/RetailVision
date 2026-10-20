package vn.retailvision.repository.monitoring;

import java.time.Instant;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.DeviceStatus;

public interface DeviceStatusRepository extends JpaRepository<DeviceStatus, String> {

    /**
     * Ghi trạng thái mới nhất theo thứ tự đến, không theo occurred_at: Last Will được dựng lúc nối
     * nên có occurred_at cũ hơn bản ONLINE đi cùng, so theo thời gian sẽ bỏ nhầm bản OFFLINE.
     */
    @Modifying
    @Query(nativeQuery = true, value = """
            insert into device_status (device_id, site_id, status, version, clock_synced, reported_at, last_seen_at)
            values (:deviceId, :siteId, :status, :version, :clockSynced, :reportedAt, :seenAt)
            on conflict (device_id) do update
                set site_id = excluded.site_id, status = excluded.status, version = excluded.version,
                    clock_synced = excluded.clock_synced, reported_at = excluded.reported_at,
                    last_seen_at = excluded.last_seen_at
            """)
    int upsert(
            @Param("deviceId") String deviceId,
            @Param("siteId") String siteId,
            @Param("status") String status,
            @Param("version") String version,
            @Param("clockSynced") boolean clockSynced,
            @Param("reportedAt") Instant reportedAt,
            @Param("seenAt") Instant seenAt);
}
