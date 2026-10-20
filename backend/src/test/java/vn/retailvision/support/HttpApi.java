package vn.retailvision.support;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.HttpCookie;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

/** Client HTTP thật cho test: giữ cookie phiên, tự gắn X-XSRF-TOKEN từ cookie XSRF-TOKEN như trình duyệt. */
public final class HttpApi {

    private static final ObjectMapper JSON = new ObjectMapper();

    private final String base;
    private final CookieManager cookies = new CookieManager(null, CookiePolicy.ACCEPT_ALL);
    private final HttpClient client;

    public HttpApi(int port) {
        this.base = "http://localhost:" + port;
        this.client = HttpClient.newBuilder().cookieHandler(cookies).connectTimeout(Duration.ofSeconds(5)).build();
    }

    public HttpResponse<String> get(String path) {
        return send(HttpRequest.newBuilder(URI.create(base + path)).GET().build());
    }

    /** Gửi kèm CSRF như SPA (header lấy từ cookie nếu có). */
    public HttpResponse<String> post(String path, Object body) {
        return send(withBody("POST", path, body, true));
    }

    public HttpResponse<String> patch(String path, Object body) {
        return send(withBody("PATCH", path, body, true));
    }

    public HttpResponse<String> put(String path, Object body) {
        return send(withBody("PUT", path, body, true));
    }

    /** Gửi mà KHÔNG kèm header CSRF (để kiểm chặn CSRF). */
    public HttpResponse<String> postWithoutCsrf(String path, Object body) {
        return send(withBody("POST", path, body, false));
    }

    public HttpResponse<String> login(String username, String password) {
        get("/api/auth/me"); // lấy cookie XSRF-TOKEN như SPA làm khi tải trang
        return post("/api/auth/login", Map.of("username", username, "password", password));
    }

    public String xsrfToken() {
        return cookies.getCookieStore().getCookies().stream()
                .filter(c -> c.getName().equals("XSRF-TOKEN"))
                .map(HttpCookie::getValue)
                .findFirst()
                .orElse(null);
    }

    public static JsonNode json(HttpResponse<String> response) {
        try {
            return JSON.readTree(response.body());
        } catch (IOException e) {
            throw new IllegalStateException("Không phải JSON: " + response.body(), e);
        }
    }

    public static List<String> setCookies(HttpResponse<?> response) {
        return response.headers().allValues("Set-Cookie");
    }

    private HttpRequest withBody(String method, String path, Object body, boolean csrf) {
        try {
            HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + path))
                    .header("Content-Type", "application/json")
                    .method(method, HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(body)));
            String token = xsrfToken();
            if (csrf && token != null) {
                b.header("X-XSRF-TOKEN", token);
            }
            return b.build();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private HttpResponse<String> send(HttpRequest request) {
        try {
            return client.send(request, HttpResponse.BodyHandlers.ofString());
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }
}
