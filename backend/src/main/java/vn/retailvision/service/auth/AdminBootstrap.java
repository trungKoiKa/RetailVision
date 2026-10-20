package vn.retailvision.service.auth;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import vn.retailvision.config.RetailVisionProperties;

/** Khi chưa có tài khoản nào, tạo ADMIN đầu tiên từ RV_ADMIN_USER / RV_ADMIN_PASS. Không bao giờ ghi mật khẩu ra log. */
@Component
public class AdminBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminBootstrap.class);

    private final UserService users;
    private final RetailVisionProperties.Admin admin;

    public AdminBootstrap(UserService users, RetailVisionProperties props) {
        this.users = users;
        this.admin = props.admin();
    }

    @Override
    public void run(ApplicationArguments args) {
        boolean configured = admin != null
                && admin.username() != null && !admin.username().isBlank()
                && admin.password() != null && !admin.password().isBlank();
        if (!configured) {
            if (users.list().isEmpty()) {
                log.warn("Chưa có tài khoản web nào. Đặt RV_ADMIN_USER và RV_ADMIN_PASS rồi khởi động lại để tạo ADMIN đầu tiên.");
            }
            return;
        }
        try {
            if (users.createFirstAdminIfEmpty(admin.username(), admin.password())) {
                log.info("Đã tạo tài khoản ADMIN đầu tiên '{}'", admin.username());
            }
        } catch (RuntimeException e) {
            log.error("Không tạo được ADMIN đầu tiên: {}", e.getMessage());
        }
    }
}
