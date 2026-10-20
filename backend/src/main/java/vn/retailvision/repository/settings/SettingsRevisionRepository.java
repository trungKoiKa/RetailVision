package vn.retailvision.repository.settings;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import vn.retailvision.domain.entity.SettingsRevision;

public interface SettingsRevisionRepository extends JpaRepository<SettingsRevision, Long> {

    Optional<SettingsRevision> findByRequestId(UUID requestId);

    List<SettingsRevision> findTop10ByOrderByRequestedAtDesc();

    Optional<SettingsRevision> findFirstByStatusOrderByAppliedRevisionDesc(String status);

    Optional<SettingsRevision> findFirstByStatusOrderByRequestedAtDesc(String status);
}
