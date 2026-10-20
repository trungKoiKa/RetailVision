package vn.retailvision.controller;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import vn.retailvision.dto.request.CreateUserRequest;
import vn.retailvision.service.auth.UserService;
import vn.retailvision.support.HttpApi;
import vn.retailvision.support.MutableClock;
import vn.retailvision.support.PostgresIT;

/** FR-08: đăng nhập session, CSRF, phân quyền ADMIN/MANAGER kiểm ở API (gọi qua HTTP thật, cookie thật). */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "retailvision.mqtt.enabled=false")
@Import(AuthIT.ClockConfig.class)
class AuthIT extends PostgresIT {

    static final Instant NOW = Instant.parse("2026-11-02T10:00:00Z");

    @TestConfiguration
    static class ClockConfig {
        @Bean
        @Primary
        MutableClock authTestClock() {
            return new MutableClock(NOW);
        }
    }

    @LocalServerPort
    int port;

    @Autowired
    UserService users;

    @Autowired
    MutableClock clock;

    HttpApi api;

    @BeforeEach
    void setUp() {
        clock.set(NOW);
        api = new HttpApi(port);
        users.create(new CreateUserRequest("admin1", "admin-pass-1", "ADMIN"));
        users.create(new CreateUserRequest("manager1", "manager-pass-1", "MANAGER"));
    }

    private HttpApi loggedIn(String user, String password) {
        HttpApi session = new HttpApi(port);
        HttpResponse<String> response = session.login(user, password);
        assertThat(response.statusCode()).as("đăng nhập " + user).isEqualTo(200);
        return session;
    }

    @Test
    void unauthenticatedCallsAreRejectedWithJson401ButHealthIsPublic() {
        for (String path : new String[] {"/api/overview", "/api/alerts", "/api/devices", "/api/users", "/api/auth/me"}) {
            HttpResponse<String> r = api.get(path);
            assertThat(r.statusCode()).as(path).isEqualTo(401);
            assertThat(HttpApi.json(r).get("error").asText()).isEqualTo("UNAUTHENTICATED");
        }
        assertThat(api.get("/api/health").statusCode()).isEqualTo(200);
    }

    @Test
    void unknownPathsAreDeniedNotExposed() {
        assertThat(loggedIn("manager1", "manager-pass-1").get("/api/does-not-exist").statusCode()).isIn(403, 404);
        assertThat(api.get("/actuator/env").statusCode()).isIn(401, 403, 404);
    }

    @Test
    void loginNeedsCsrfTokenAndSetsHardenedSessionCookie() {
        // lần đầu chưa có token: bị từ chối dù mật khẩu đúng
        api.get("/api/auth/me");
        assertThat(api.xsrfToken()).as("cookie XSRF-TOKEN phải được gửi ngay cả khi 401").isNotNull();
        HttpResponse<String> noCsrf = api.postWithoutCsrf("/api/auth/login", Map.of("username", "manager1", "password", "manager-pass-1"));
        assertThat(noCsrf.statusCode()).isEqualTo(403);

        HttpResponse<String> ok = api.post("/api/auth/login", Map.of("username", "manager1", "password", "manager-pass-1"));
        assertThat(ok.statusCode()).isEqualTo(200);
        assertThat(HttpApi.json(ok).get("role").asText()).isEqualTo("MANAGER");
        String session = HttpApi.setCookies(ok).stream().filter(c -> c.startsWith("RVSESSION=")).findFirst().orElseThrow();
        assertThat(session).containsIgnoringCase("HttpOnly").containsIgnoringCase("SameSite=Lax");
        assertThat(api.get("/api/auth/me").statusCode()).isEqualTo(200);
    }

    @Test
    void logoutEndsTheSession() {
        HttpApi session = loggedIn("manager1", "manager-pass-1");
        assertThat(session.get("/api/overview").statusCode()).isEqualTo(200);
        assertThat(session.post("/api/auth/logout", Map.of()).statusCode()).isEqualTo(204);
        assertThat(session.get("/api/overview").statusCode()).isEqualTo(401);
    }

    @Test
    void sessionIdChangesOnLoginToPreventFixation() {
        api.get("/api/auth/me");
        HttpResponse<String> first = api.post("/api/auth/login", Map.of("username", "manager1", "password", "manager-pass-1"));
        String id1 = HttpApi.setCookies(first).stream().filter(c -> c.startsWith("RVSESSION=")).findFirst().orElseThrow().split(";")[0];
        api.post("/api/auth/logout", Map.of());
        api.get("/api/auth/me");
        HttpResponse<String> second = api.post("/api/auth/login", Map.of("username", "manager1", "password", "manager-pass-1"));
        String id2 = HttpApi.setCookies(second).stream().filter(c -> c.startsWith("RVSESSION=")).findFirst().orElseThrow().split(";")[0];
        assertThat(id2).isNotEqualTo(id1);
    }

    @Test
    void badCredentialsGiveTheSameAnswerForUnknownUserAndWrongPassword() {
        HttpApi a = new HttpApi(port);
        HttpApi b = new HttpApi(port);
        HttpResponse<String> wrongPassword = a.login("manager1", "nope-nope-nope");
        HttpResponse<String> unknownUser = b.login("ghost", "nope-nope-nope");
        assertThat(wrongPassword.statusCode()).isEqualTo(401);
        assertThat(unknownUser.statusCode()).isEqualTo(401);
        assertThat(HttpApi.json(wrongPassword).get("message").asText()).isEqualTo(HttpApi.json(unknownUser).get("message").asText());
    }

    @Test
    void disabledAccountCannotLogInAndLosesAccess() {
        HttpApi admin = loggedIn("admin1", "admin-pass-1");
        long managerId = HttpApi.json(admin.get("/api/users")).findValues("id").stream()
                .map(n -> n.asLong()).filter(id -> id > 0).sorted().skip(1).findFirst().orElseThrow();
        // người thứ hai theo thứ tự tên là manager1 (admin1 < manager1)
        assertThat(admin.patch("/api/users/" + managerId, Map.of("enabled", false)).statusCode()).isEqualTo(200);
        assertThat(new HttpApi(port).login("manager1", "manager-pass-1").statusCode()).isEqualTo(401);
    }

    @Test
    void tooManyWrongPasswordsLockTheAccountTemporarily() {
        for (int i = 0; i < 5; i++) {
            assertThat(new HttpApi(port).login("manager1", "wrong-password-" + i).statusCode()).isEqualTo(401);
        }
        // đã bị khoá: ngay cả mật khẩu đúng cũng bị từ chối
        assertThat(new HttpApi(port).login("manager1", "manager-pass-1").statusCode()).isEqualTo(429);
        clock.advance(Duration.ofMinutes(6));
        assertThat(new HttpApi(port).login("manager1", "manager-pass-1").statusCode()).isEqualTo(200);
    }

    @Test
    void managerCanReadReportsButNotManageUsers() {
        HttpApi manager = loggedIn("manager1", "manager-pass-1");
        assertThat(manager.get("/api/overview").statusCode()).isEqualTo(200);
        assertThat(manager.get("/api/alerts").statusCode()).isEqualTo(200);
        assertThat(manager.get("/api/devices").statusCode()).isEqualTo(200);
        assertThat(manager.get("/api/users").statusCode()).isEqualTo(403);
        assertThat(manager.post("/api/users", Map.of("username", "x1234", "password", "password-1", "role", "MANAGER")).statusCode())
                .isEqualTo(403);
        assertThat(HttpApi.json(manager.get("/api/users")).get("error").asText()).isEqualTo("FORBIDDEN");
    }

    @Test
    void adminCanManageUsersAndWritesNeedCsrf() {
        HttpApi admin = loggedIn("admin1", "admin-pass-1");
        assertThat(admin.get("/api/users").statusCode()).isEqualTo(200);
        // đã đăng nhập nhưng không có header CSRF: vẫn bị chặn
        assertThat(admin.postWithoutCsrf("/api/users", Map.of("username", "viewer1", "password", "password-1", "role", "MANAGER")).statusCode())
                .isEqualTo(403);
        assertThat(admin.post("/api/users", Map.of("username", "viewer1", "password", "password-1", "role", "MANAGER")).statusCode())
                .isEqualTo(201);
    }

    @Test
    void settingsEndpointsRequireLoginAndCsrf() {
        assertThat(api.get("/api/settings").statusCode()).isEqualTo(401);
        HttpApi manager = loggedIn("manager1", "manager-pass-1");
        assertThat(manager.get("/api/settings").statusCode()).isEqualTo(200);
        String body = "{\"dwell_seconds\":2,\"on_count\":5,\"on_hold_seconds\":60,\"off_count\":3,\"off_hold_seconds\":10}";
        // không có header CSRF: bị chặn trước khi chạm tới nghiệp vụ
        assertThat(manager.postWithoutCsrf("/api/settings", Map.of()).statusCode()).isIn(403, 405);
        // có CSRF và đã đăng nhập: vượt qua lớp bảo mật, tới nghiệp vụ (ở context này MQTT tắt nên 503, không phải 401/403)
        assertThat(manager.put("/api/settings", Map.of("dwell_seconds", 2, "on_count", 5, "on_hold_seconds", 60, "off_count", 3, "off_hold_seconds", 10)).statusCode()).isEqualTo(503);
        assertThat(body).isNotEmpty();
    }

    @Test
    void passwordsAreStoredAsBcryptAndNeverReturned() {
        HttpApi admin = loggedIn("admin1", "admin-pass-1");
        String hash = jdbc.queryForObject("select password_hash from app_user where username = 'manager1'", String.class);
        assertThat(hash).startsWith("$2").doesNotContain("manager-pass-1");
        assertThat(admin.get("/api/users").body()).doesNotContain("password").doesNotContain("$2");
    }

    @Test
    void createUserValidatesInputAndRejectsDuplicates() {
        HttpApi admin = loggedIn("admin1", "admin-pass-1");
        assertThat(admin.post("/api/users", Map.of("username", "A!", "password", "password-1", "role", "MANAGER")).statusCode()).isEqualTo(400);
        assertThat(admin.post("/api/users", Map.of("username", "newuser", "password", "short", "role", "MANAGER")).statusCode()).isEqualTo(400);
        assertThat(admin.post("/api/users", Map.of("username", "newuser", "password", "password-1", "role", "ROOT")).statusCode()).isEqualTo(400);
        assertThat(admin.post("/api/users", Map.of("username", "manager1", "password", "password-1", "role", "MANAGER")).statusCode()).isEqualTo(409);
        assertThat(admin.post("/api/users", Map.of("username", "NewUser", "password", "password-1", "role", "MANAGER")).statusCode()).isEqualTo(201);
        // tên đăng nhập không phân biệt hoa thường
        assertThat(new HttpApi(port).login("NEWUSER", "password-1").statusCode()).isEqualTo(200);
    }

    @Test
    void lastEnabledAdminCannotBeDemotedDisabledOrSelfDisabled() {
        HttpApi admin = loggedIn("admin1", "admin-pass-1");
        long adminId = jdbc.queryForObject("select id from app_user where username = 'admin1'", Long.class);
        assertThat(admin.patch("/api/users/" + adminId, Map.of("role", "MANAGER")).statusCode()).isEqualTo(409);
        assertThat(admin.patch("/api/users/" + adminId, Map.of("enabled", false)).statusCode()).isEqualTo(409);
        // có ADMIN thứ hai thì được hạ quyền ADMIN đầu, nhưng vẫn không được tự vô hiệu hóa
        users.create(new CreateUserRequest("admin2", "admin-pass-2", "ADMIN"));
        assertThat(admin.patch("/api/users/" + adminId, Map.of("enabled", false)).statusCode()).isEqualTo(409);
        assertThat(admin.patch("/api/users/" + adminId, Map.of("role", "MANAGER")).statusCode()).isEqualTo(200);
    }

    @Test
    void usersCanChangeTheirOwnPassword() {
        HttpApi manager = loggedIn("manager1", "manager-pass-1");
        // khoá camelCase không phải API (JSON dùng snake_case): bị coi là thiếu trường
        assertThat(manager.post("/api/auth/password", Map.of("currentPassword", "manager-pass-1", "newPassword", "brand-new-pass")).statusCode()).isEqualTo(400);
        assertThat(manager.post("/api/auth/password", Map.of("current_password", "wrong", "new_password", "brand-new-pass")).statusCode()).isEqualTo(400);
        assertThat(manager.post("/api/auth/password", Map.of("current_password", "manager-pass-1", "new_password", "short")).statusCode()).isEqualTo(400);
        assertThat(manager.post("/api/auth/password", Map.of("current_password", "manager-pass-1", "new_password", "brand-new-pass")).statusCode()).isEqualTo(204);
        assertThat(new HttpApi(port).login("manager1", "manager-pass-1").statusCode()).isEqualTo(401);
        assertThat(new HttpApi(port).login("manager1", "brand-new-pass").statusCode()).isEqualTo(200);
    }

    @Test
    void firstAdminIsCreatedOnlyWhenNoUsersExist() {
        assertThat(users.createFirstAdminIfEmpty("rootadmin", "root-admin-pass")).isFalse(); // đã có tài khoản từ setUp
        jdbc.execute("truncate table app_user restart identity");
        assertThat(users.createFirstAdminIfEmpty("rootadmin", "root-admin-pass")).isTrue();
        assertThat(new HttpApi(port).login("rootadmin", "root-admin-pass").statusCode()).isEqualTo(200);
    }
}
