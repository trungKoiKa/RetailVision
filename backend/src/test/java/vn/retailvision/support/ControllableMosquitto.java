package vn.retailvision.support;

import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Mosquitto cục bộ có thể bật/tắt trên cùng một cổng (test phục hồi). Tắt bằng kill nên không lưu
 * persistence; test cần persistence dùng {@link DockerMosquitto}.
 */
public final class ControllableMosquitto implements AutoCloseable {

    private final Path bin = MosquittoBroker.binary();
    private final int port;
    private Process process;

    public ControllableMosquitto() {
        try (ServerSocket s = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            this.port = s.getLocalPort();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    public boolean available() {
        return bin != null;
    }

    public int port() {
        return port;
    }

    public void start() {
        try {
            Path conf = Files.createTempFile("mosquitto-ctl", ".conf");
            Files.writeString(conf, "listener " + port + " 127.0.0.1\nallow_anonymous true\npersistence false\n");
            process = new ProcessBuilder(bin.toString(), "-c", conf.toString())
                    .redirectErrorStream(true)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .start();
            long deadline = System.currentTimeMillis() + 8000;
            while (System.currentTimeMillis() < deadline) {
                try (Socket ignored = new Socket(InetAddress.getLoopbackAddress(), port)) {
                    return;
                } catch (IOException e) {
                    Thread.sleep(100);
                }
            }
            throw new IllegalStateException("Mosquitto không lên trên cổng " + port);
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }

    public void stop() {
        if (process != null) {
            process.destroyForcibly();
            try {
                process.waitFor();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            process = null;
        }
    }

    @Override
    public void close() {
        stop();
    }
}
