package vn.retailvision.support;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Nền cho test cần PostgreSQL thật (Testcontainers). Một container dùng chung cho cả lượt chạy;
 * mỗi test bắt đầu với các bảng sự kiện rỗng. MQTT tắt trừ khi test bật lại.
 */
@SpringBootTest(properties = "retailvision.mqtt.enabled=false")
public abstract class PostgresIT {

    static final PostgreSQLContainer<?> POSTGRES = new PostgreSQLContainer<>("postgres:17-alpine");

    static {
        POSTGRES.start();
    }

    @DynamicPropertySource
    static void database(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }

    @Autowired
    protected JdbcTemplate jdbc;

    @BeforeEach
    void cleanTables() {
        jdbc.execute("""
                truncate table telemetry_minute, alert_transition, alert_event, crossing_event,
                    edge_session, device_status, app_user restart identity cascade
                """);
    }

    protected long count(String table) {
        return jdbc.queryForObject("select count(*) from " + table, Long.class);
    }
}
