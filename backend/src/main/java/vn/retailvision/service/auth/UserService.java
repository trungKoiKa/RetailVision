package vn.retailvision.service.auth;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.util.List;
import java.util.regex.Pattern;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.retailvision.domain.entity.AppUser;
import vn.retailvision.dto.request.CreateUserRequest;
import vn.retailvision.dto.request.UpdateUserRequest;
import vn.retailvision.dto.response.UserView;
import vn.retailvision.exception.ApiException;
import vn.retailvision.repository.auth.AppUserRepository;

@Service
public class UserService {

    static final Pattern USERNAME = Pattern.compile("[a-z0-9._-]{3,32}");
    static final int MIN_PASSWORD = 8;
    static final int MAX_PASSWORD_BYTES = 72; // giới hạn của BCrypt

    private final AppUserRepository users;
    private final PasswordEncoder encoder;
    private final Clock clock;

    public UserService(AppUserRepository users, PasswordEncoder encoder, Clock clock) {
        this.users = users;
        this.encoder = encoder;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public List<UserView> list() {
        return users.findAllByOrderByUsernameAsc().stream().map(UserService::view).toList();
    }

    @Transactional
    public UserView create(CreateUserRequest request) {
        String username = request.username().trim().toLowerCase();
        if (!USERNAME.matcher(username).matches()) {
            throw ApiException.badRequest("Tên đăng nhập gồm 3–32 ký tự a–z, 0–9, '.', '_' hoặc '-'");
        }
        checkPassword(request.password());
        if (users.existsByUsername(username)) {
            throw ApiException.conflict("Tên đăng nhập đã tồn tại");
        }
        return view(users.save(new AppUser(username, encoder.encode(request.password()), request.role())));
    }

    @Transactional
    public UserView update(long id, UpdateUserRequest request, String actingUsername) {
        AppUser user = users.findById(id).orElseThrow(() -> ApiException.notFound("Không có tài khoản"));
        boolean losesAdmin = "ADMIN".equals(user.getRole())
                && user.isEnabled()
                && ((request.role() != null && !"ADMIN".equals(request.role()))
                        || Boolean.FALSE.equals(request.enabled()));
        if (losesAdmin && users.countByRoleAndEnabledTrue("ADMIN") <= 1) {
            throw ApiException.conflict("Phải còn ít nhất một ADMIN đang hoạt động");
        }
        if (Boolean.FALSE.equals(request.enabled()) && user.getUsername().equals(actingUsername)) {
            throw ApiException.conflict("Không thể tự vô hiệu hóa tài khoản đang dùng");
        }
        if (request.role() != null) {
            user.setRole(request.role());
        }
        if (request.enabled() != null) {
            user.setEnabled(request.enabled());
        }
        if (request.password() != null) {
            checkPassword(request.password());
            user.setPasswordHash(encoder.encode(request.password()));
        }
        return view(user);
    }

    @Transactional
    public void changeOwnPassword(String username, String current, String next) {
        AppUser user = users.findByUsername(username).orElseThrow(() -> ApiException.notFound("Không có tài khoản"));
        if (!encoder.matches(current, user.getPasswordHash())) {
            throw ApiException.badRequest("Mật khẩu hiện tại không đúng");
        }
        checkPassword(next);
        user.setPasswordHash(encoder.encode(next));
    }

    @Transactional
    public void touchLogin(String username) {
        users.findByUsername(username).ifPresent(u -> u.setLastLoginAt(clock.instant()));
    }

    /** Tạo ADMIN đầu tiên khi chưa có tài khoản nào. Trả true nếu đã tạo. */
    @Transactional
    public boolean createFirstAdminIfEmpty(String username, String password) {
        if (users.count() > 0) {
            return false;
        }
        create(new CreateUserRequest(username, password, "ADMIN"));
        return true;
    }

    private static void checkPassword(String password) {
        if (password.length() < MIN_PASSWORD) {
            throw ApiException.badRequest("Mật khẩu tối thiểu " + MIN_PASSWORD + " ký tự");
        }
        if (password.getBytes(StandardCharsets.UTF_8).length > MAX_PASSWORD_BYTES) {
            throw ApiException.badRequest("Mật khẩu quá dài (tối đa " + MAX_PASSWORD_BYTES + " byte)");
        }
    }

    private static UserView view(AppUser u) {
        return new UserView(u.getId(), u.getUsername(), u.getRole(), u.isEnabled(), u.getCreatedAt(), u.getLastLoginAt());
    }
}
