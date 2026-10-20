package vn.retailvision.repository.event;

import java.time.Instant;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import vn.retailvision.domain.entity.EdgeSession;

public interface EdgeSessionRepository extends JpaRepository<EdgeSession, UUID> {

    /** Tạo phiên ở bản tin đầu tiên của nó; đã có thì bỏ qua. */
    @Modifying
    @Query(nativeQuery = true, value = """
            insert into edge_session (session_id, device_id, started_at, config_version)
            values (:sessionId, :deviceId, :startedAt, :configVersion)
            on conflict (session_id) do nothing
            """)
    int insertIgnore(
            @Param("sessionId") UUID sessionId,
            @Param("deviceId") String deviceId,
            @Param("startedAt") Instant startedAt,
            @Param("configVersion") String configVersion);
}
