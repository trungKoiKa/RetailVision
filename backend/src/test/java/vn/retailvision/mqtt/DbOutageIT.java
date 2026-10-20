package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import com.github.dockerjava.api.model.ExposedPort;
import com.github.dockerjava.api.model.PortBinding;
import com.github.dockerjava.api.model.Ports;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.time.Duration;
import java.util.UUID;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.MosquittoBroker;

/**
 * DB sập thật (dừng container PostgreSQL) trong lúc sự kiện đang tới: backend không ack, ngắt và nối
 * lại để broker gửi lại; khi DB trở lại mọi sự kiện vào đúng một lần.
 */
@SpringBootTest(properties = {"retailvision.mqtt.enabled=true", "retailvision.mqtt.restart-delay-seconds=1", "logging.level.vn.retailvision.mqtt=DEBUG"})
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_CLASS)
class DbOutageIT {

    static int DB_PORT;
    static PostgreSQLContainer<?> DB;

    static {
        // cổng chọn trước có thể bị tiến trình khác chiếm trước khi Docker gắn: thử lại với cổng khác
        for (int attempt = 0; ; attempt++) {
            final int port = freePort();
            DB_PORT = port;
            DB = new PostgreSQLContainer<>("postgres:17-alpine")
                    .withCreateContainerCmdModifier(cmd -> cmd.getHostConfig()
                            .withPortBindings(new PortBinding(Ports.Binding.bindPort(port), new ExposedPort(5432))));
            try {
                DB.start();
                break;
            } catch (org.testcontainers.containers.ContainerLaunchException e) {
                DB.stop();
                if (attempt >= 4) {
                    throw e;
                }
            }
        }
    }

    @BeforeAll
    static void requireMosquitto() {
        Assumptions.assumeTrue(MosquittoBroker.available(), "không có mosquitto");
    }

    @AfterAll
    static void stopDb() {
        DB.stop();
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> "jdbc:postgresql://127.0.0.1:" + DB_PORT + "/" + DB.getDatabaseName());
        registry.add("spring.datasource.username", DB::getUsername);
        registry.add("spring.datasource.password", DB::getPassword);
        registry.add("retailvision.mqtt.host", () -> "127.0.0.1");
        registry.add("retailvision.mqtt.port", MosquittoBroker::port);
        registry.add("retailvision.mqtt.username", () -> "");
    }

    @Autowired
    JdbcTemplate jdbc;

    @Autowired
    MqttConnectionManager manager;

    private static int freePort() {
        try (ServerSocket s = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            return s.getLocalPort();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private long count() {
        return jdbc.queryForObject("select count(*) from crossing_event", Long.class);
    }

    /** Chờ tới khi DB thật sự trả lời truy vấn (cổng Docker có thể nhận kết nối trước khi PostgreSQL sẵn sàng). */
    private static void awaitDbReady() {
        await().atMost(Duration.ofSeconds(60)).ignoreExceptions().until(() -> {
            try (var c = java.sql.DriverManager.getConnection(
                            "jdbc:postgresql://127.0.0.1:" + DB_PORT + "/" + DB.getDatabaseName() + "?connectTimeout=3&socketTimeout=3",
                            DB.getUsername(), DB.getPassword());
                    var st = c.createStatement();
                    var rs = st.executeQuery("select 1")) {
                return rs.next();
            }
        });
    }

    @Test
    void eventsArrivingWhileTheDatabaseIsDownAreStoredExactlyOnceAfterItReturns() throws Exception {
        await().atMost(Duration.ofSeconds(15)).until(manager::isConnected);

        DB.getDockerClient().stopContainerCmd(DB.getContainerId()).withTimeout(5).exec(); // DB sập
        String base = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"));
        MqttClient publisher = new MqttClient("tcp://127.0.0.1:" + MosquittoBroker.port(), "pub-" + UUID.randomUUID(), new MemoryPersistence());
        publisher.connect();
        for (int i = 0; i < 3; i++) {
            publisher.publish(
                    "retailvision/v1/site01/edge01/events/crossing",
                    base.replace("7a2e4c6b-1d3f-4a5b-8c9d-0e1f2a3b4c5e", UUID.randomUUID().toString()).getBytes(),
                    1,
                    false);
        }
        publisher.disconnect();
        publisher.close();

        Thread.sleep(8000); // backend thử, thất bại, không ack, ngắt/nối lại nhiều lần

        DB.getDockerClient().startContainerCmd(DB.getContainerId()).exec(); // DB trở lại
        awaitDbReady();
        await().atMost(Duration.ofSeconds(60)).untilAsserted(() -> assertThat(count()).isEqualTo(3)); // DB đã sẵn sàng: phải đủ trong vòng 1 phút
        Thread.sleep(3000);
        assertThat(count()).isEqualTo(3); // đủ, không trùng dù bị gửi lại nhiều lần
    }
}
