package vn.retailvision.repository.auth;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import vn.retailvision.domain.entity.AppUser;

public interface AppUserRepository extends JpaRepository<AppUser, Long> {

    Optional<AppUser> findByUsername(String username);

    boolean existsByUsername(String username);

    List<AppUser> findAllByOrderByUsernameAsc();

    long countByRoleAndEnabledTrue(String role);
}
