package vn.retailvision.controller;

import static org.assertj.core.api.Assertions.assertThat;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import vn.retailvision.support.PostgresIT;

/**
 * T18 phía backend: làm mới dashboard dồn dập không mở thêm kết nối DB vượt hồ chứa, không làm tăng
 * luồng mãi, và mọi phản hồi vẫn đúng.
 */
@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "retailvision.mqtt.enabled=false")
class RefreshStressIT extends PostgresIT {

    @LocalServerPort
    int port;

    @Autowired
    javax.sql.DataSource dataSource;

    @Test
    void manyDashboardRefreshesKeepConnectionsAndThreadsBounded() throws Exception {
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        String[] paths = {"/api/overview", "/api/alerts?size=20", "/api/devices", "/api/health"};
        int threadsBefore = Thread.activeCount();

        ExecutorService pool = Executors.newFixedThreadPool(12);
        List<Future<Long>> futures = new ArrayList<>();
        for (int t = 0; t < 12; t++) {
            final int offset = t;
            Callable<Long> task = () -> {
                long worst = 0;
                for (int i = 0; i < 150; i++) {
                    String path = paths[(offset + i) % paths.length];
                    long start = System.nanoTime();
                    HttpResponse<String> response = client.send(
                            HttpRequest.newBuilder(URI.create("http://localhost:" + port + path)).GET().build(),
                            HttpResponse.BodyHandlers.ofString());
                    worst = Math.max(worst, (System.nanoTime() - start) / 1_000_000);
                    assertThat(response.statusCode()).as(path).isEqualTo(200);
                }
                return worst;
            };
            futures.add(pool.submit(task));
        }
        long worstMs = 0;
        for (Future<Long> f : futures) {
            worstMs = Math.max(worstMs, f.get());
        }
        pool.shutdown();

        var hikari = dataSource.unwrap(com.zaxxer.hikari.HikariDataSource.class);
        assertThat(hikari.getHikariPoolMXBean().getTotalConnections())
                .as("kết nối trong hồ sau 1800 request")
                .isLessThanOrEqualTo(hikari.getMaximumPoolSize()); // dashboard làm mới không mở thêm kết nối ngoài hồ
        assertThat(hikari.getHikariPoolMXBean().getActiveConnections()).as("kết nối còn bị giữ").isZero();
        assertThat(Thread.activeCount() - threadsBefore).as("số luồng tăng thêm").isLessThan(40);
        assertThat(worstMs).as("request chậm nhất (ms)").isLessThan(5000);
    }
}
