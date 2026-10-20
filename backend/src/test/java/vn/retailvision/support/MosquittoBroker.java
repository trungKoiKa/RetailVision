package vn.retailvision.support;

import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Mosquitto thật cho test (một tiến trình dùng chung cả lượt chạy, cổng ngẫu nhiên, không tài khoản).
 * Tìm file chạy theo thứ tự: biến RV_MOSQUITTO_BIN, PATH, thư mục cài mặc định trên Windows.
 * Không có thì {@link #available()} trả false và test MQTT được bỏ qua.
 */
public final class MosquittoBroker {

    private static final Path BIN = findBinary();
    private static int port;
    private static Process process;

    private MosquittoBroker() {}

    public static boolean available() {
        return BIN != null;
    }

    public static synchronized int port() {
        if (BIN == null) {
            return 1; // không dùng tới: test sẽ bị bỏ qua
        }
        if (process == null) {
            start();
        }
        return port;
    }

    private static void start() {
        try {
            try (ServerSocket s = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
                port = s.getLocalPort();
            }
            Path conf = Files.createTempFile("mosquitto-test", ".conf");
            Files.writeString(conf, "listener " + port + " 127.0.0.1\nallow_anonymous true\npersistence false\n");
            process = new ProcessBuilder(BIN.toString(), "-c", conf.toString())
                    .redirectErrorStream(true)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .start();
            Runtime.getRuntime().addShutdownHook(new Thread(process::destroyForcibly));
            long deadline = System.currentTimeMillis() + 8000;
            while (System.currentTimeMillis() < deadline) {
                try (Socket ignored = new Socket(InetAddress.getLoopbackAddress(), port)) {
                    return;
                } catch (IOException e) {
                    Thread.sleep(100);
                }
            }
            throw new IllegalStateException("Mosquitto không khởi động được trên cổng " + port);
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException("Không chạy được Mosquitto", e);
        }
    }

    private static Path findBinary() {
        String fromEnv = System.getenv("RV_MOSQUITTO_BIN");
        if (fromEnv != null && Files.isRegularFile(Path.of(fromEnv))) {
            return Path.of(fromEnv);
        }
        String pathVar = System.getenv("PATH");
        if (pathVar != null) {
            for (String dir : pathVar.split(java.io.File.pathSeparator)) {
                for (String name : new String[] {"mosquitto.exe", "mosquitto"}) {
                    Path candidate = Path.of(dir, name);
                    if (Files.isRegularFile(candidate)) {
                        return candidate;
                    }
                }
            }
        }
        Path windows = Path.of("C:\\Program Files\\mosquitto\\mosquitto.exe");
        return Files.isRegularFile(windows) ? windows : null;
    }
}
