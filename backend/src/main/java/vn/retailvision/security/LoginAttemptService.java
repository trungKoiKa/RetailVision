package vn.retailvision.security;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * Chống dò mật khẩu: quá {@value #MAX_FAILURES} lần sai trong {@value #WINDOW_MINUTES} phút thì khoá
 * tên đăng nhập đó {@value #LOCK_MINUTES} phút. Tên không tồn tại cũng bị đếm như nhau để không lộ tài khoản
 * nào có thật. Giữ trong RAM: restart backend thì xoá (đủ cho mạng LAN).
 */
@Component
public class LoginAttemptService {

    static final int MAX_FAILURES = 5;
    static final long WINDOW_MINUTES = 10;
    static final long LOCK_MINUTES = 5;

    private final Clock clock;
    private final Map<String, Deque<Instant>> failures = new ConcurrentHashMap<>();
    private final Map<String, Instant> lockedUntil = new ConcurrentHashMap<>();

    public LoginAttemptService(Clock clock) {
        this.clock = clock;
    }

    public boolean isLocked(String username) {
        Instant until = lockedUntil.get(key(username));
        if (until == null) {
            return false;
        }
        if (clock.instant().isBefore(until)) {
            return true;
        }
        lockedUntil.remove(key(username));
        failures.remove(key(username));
        return false;
    }

    public void recordFailure(String username) {
        Instant now = clock.instant();
        Deque<Instant> recent = failures.computeIfAbsent(key(username), k -> new ArrayDeque<>());
        synchronized (recent) {
            recent.addLast(now);
            Instant cutoff = now.minus(Duration.ofMinutes(WINDOW_MINUTES));
            while (!recent.isEmpty() && recent.peekFirst().isBefore(cutoff)) {
                recent.removeFirst();
            }
            if (recent.size() >= MAX_FAILURES) {
                lockedUntil.put(key(username), now.plus(Duration.ofMinutes(LOCK_MINUTES)));
            }
        }
    }

    public void recordSuccess(String username) {
        failures.remove(key(username));
        lockedUntil.remove(key(username));
    }

    private static String key(String username) {
        return username == null ? "" : username.toLowerCase();
    }
}
