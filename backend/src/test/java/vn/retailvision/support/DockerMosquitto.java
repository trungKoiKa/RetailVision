package vn.retailvision.support;

import com.github.dockerjava.api.model.ExposedPort;
import com.github.dockerjava.api.model.PortBinding;
import com.github.dockerjava.api.model.Ports;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.images.builder.Transferable;
import org.testcontainers.utility.DockerImageName;

/**
 * Mosquitto trong Docker với persistence bật. Dừng bằng SIGTERM nên broker kịp ghi hàng đợi xuống đĩa,
 * rồi bật lại trên cùng cổng: mô phỏng "restart broker khi còn hàng đợi" (T25).
 */
public final class DockerMosquitto implements AutoCloseable {

    private static final String CONF = """
            listener 1883
            allow_anonymous true
            persistence true
            persistence_location /mosquitto/data/
            autosave_interval 1
            max_queued_messages 1000
            """;

    private final int hostPort;
    private final GenericContainer<?> container;

    public DockerMosquitto() {
        try (ServerSocket s = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            this.hostPort = s.getLocalPort();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        this.container = new GenericContainer<>(DockerImageName.parse("eclipse-mosquitto:2"))
                .withExposedPorts(1883)
                .withCopyToContainer(Transferable.of(CONF), "/mosquitto/config/mosquitto.conf")
                .withCreateContainerCmdModifier(cmd -> cmd.getHostConfig()
                        .withPortBindings(new PortBinding(Ports.Binding.bindPort(hostPort), new ExposedPort(1883))));
    }

    public int port() {
        return hostPort;
    }

    public void start() {
        container.start();
        awaitPort();
    }

    /** SIGTERM (chờ tối đa 10 s): broker lưu persistence rồi thoát. */
    public void stopGracefully() {
        container.getDockerClient().stopContainerCmd(container.getContainerId()).withTimeout(10).exec();
    }

    /** Bật lại chính container đó (giữ nguyên dữ liệu persistence và cổng). */
    public void restart() {
        container.getDockerClient().startContainerCmd(container.getContainerId()).exec();
        awaitPort();
    }

    private void awaitPort() {
        long deadline = System.currentTimeMillis() + 15000;
        while (System.currentTimeMillis() < deadline) {
            try (Socket ignored = new Socket(InetAddress.getLoopbackAddress(), hostPort)) {
                return;
            } catch (IOException e) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
        throw new IllegalStateException("Mosquitto (Docker) không lên trên cổng " + hostPort);
    }

    @Override
    public void close() {
        container.stop();
    }
}
