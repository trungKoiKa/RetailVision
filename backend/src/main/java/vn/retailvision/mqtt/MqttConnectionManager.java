package vn.retailvision.mqtt;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.SmartLifecycle;
import org.springframework.stereotype.Component;
import vn.retailvision.config.RetailVisionProperties;

/**
 * Kết nối tới Mosquitto với cleanSession=false, client-id cố định và ack thủ công: broker giữ các bản
 * tin QoS 1 chưa ack (kể cả lúc backend tắt) và gửi lại khi nối lại.
 *
 * <p>Ack chỉ gửi sau khi {@link MqttMessageProcessor} báo ACK (đã commit DB). Khi gặp lỗi hạ tầng,
 * bản tin không được ack và kết nối được ngắt rồi nối lại sau {@code restartDelaySeconds} để broker
 * gửi lại, vì Paho chỉ gửi lại bản tin chưa ack khi nối lại.
 */
@Component
@ConditionalOnProperty(prefix = "retailvision.mqtt", name = "enabled", havingValue = "true", matchIfMissing = true)
public class MqttConnectionManager implements MqttCallbackExtended, SmartLifecycle {

    private static final Logger log = LoggerFactory.getLogger(MqttConnectionManager.class);

    private final RetailVisionProperties.Mqtt props;
    private final MqttMessageProcessor processor;
    private final MqttRouter router;
    private final ScheduledExecutorService scheduler =
            Executors.newSingleThreadScheduledExecutor(r -> {
                Thread t = new Thread(r, "mqtt-connection");
                t.setDaemon(true);
                return t;
            });
    private final AtomicBoolean running = new AtomicBoolean(false);
    private final AtomicBoolean restartPending = new AtomicBoolean(false);
    /** Cầu dao: sau lỗi hạ tầng, tới mốc này không xử lý bản tin QoS 1 (để không chặn luồng nhận bằng các lần thử DB). */
    private final AtomicLong retryBlockedUntilNanos = new AtomicLong(0);
    private volatile MqttClient client;

    public MqttConnectionManager(RetailVisionProperties props, MqttMessageProcessor processor, MqttRouter router) {
        this.props = props.mqtt();
        this.processor = processor;
        this.router = router;
    }

    public boolean isConnected() {
        MqttClient c = client;
        return c != null && c.isConnected();
    }

    // --- vòng đời --------------------------------------------------------

    @Override
    public void start() {
        if (running.compareAndSet(false, true)) {
            scheduler.execute(this::connectWithRetry);
        }
    }

    @Override
    public void stop() {
        running.set(false);
        scheduler.shutdownNow();
        MqttClient c = client;
        if (c != null) {
            try {
                if (c.isConnected()) {
                    c.disconnect(2000);
                }
                c.close();
            } catch (MqttException e) {
                log.warn("Lỗi khi đóng kết nối MQTT: {}", e.getMessage());
            }
        }
    }

    @Override
    public boolean isRunning() {
        return running.get();
    }

    // --- kết nối ---------------------------------------------------------

    private MqttConnectOptions options() {
        MqttConnectOptions o = new MqttConnectOptions();
        o.setCleanSession(false);
        o.setAutomaticReconnect(true);
        o.setKeepAliveInterval(15);
        o.setConnectionTimeout(10);
        o.setMaxInflight(100);
        if (props.username() != null && !props.username().isBlank()) {
            o.setUserName(props.username());
            o.setPassword(props.password() == null ? new char[0] : props.password().toCharArray());
        }
        return o;
    }

    private void connectWithRetry() {
        long delayMs = props.restartDelaySeconds() * 1000L;
        while (running.get()) {
            try {
                if (client == null) {
                    String uri = "tcp://" + props.host() + ":" + props.port();
                    MqttClient c = new MqttClient(uri, props.clientId(), new MemoryPersistence());
                    c.setManualAcks(true);
                    c.setCallback(this);
                    client = c;
                }
                client.connect(options());
                return;
            } catch (MqttException e) {
                log.warn("Chưa nối được MQTT {}:{} ({}); thử lại sau {} s", props.host(), props.port(),
                        e.getMessage(), props.restartDelaySeconds());
                try {
                    Thread.sleep(delayMs);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }

    private void scheduleRestart() {
        if (running.get() && restartPending.compareAndSet(false, true)) {
            scheduler.schedule(this::restart, props.restartDelaySeconds(), TimeUnit.SECONDS);
        }
    }

    private void restart() {
        try {
            MqttClient c = client;
            if (c != null) {
                log.warn("Ngắt kết nối MQTT để broker gửi lại các bản tin chưa ack");
                try {
                    c.disconnectForcibly(1000, 1000, false);
                } catch (MqttException e) {
                    log.warn("disconnectForcibly: {}", e.getMessage());
                }
            }
            connectWithRetry();
        } finally {
            restartPending.set(false);
        }
    }

    // --- callback của Paho -----------------------------------------------

    @Override
    public void connectComplete(boolean reconnect, String serverUri) {
        try {
            client.subscribe(router.subscriptionTopics(), router.subscriptionQos());
            log.info("Đã nối MQTT {} ({}) và đăng ký {} topic", serverUri, reconnect ? "nối lại" : "lần đầu",
                    router.subscriptionTopics().length);
        } catch (MqttException e) {
            log.error("Đăng ký topic thất bại: {}", e.getMessage());
        }
    }

    @Override
    public void connectionLost(Throwable cause) {
        log.warn("Mất kết nối MQTT: {}", cause == null ? "?" : cause.getMessage());
    }

    @Override
    public void messageArrived(String topic, MqttMessage message) {
        log.debug("Nhận bản tin id={} qos={} dup={} topic={}", message.getId(), message.getQos(), message.isDuplicate(), topic);
        if (message.getQos() > 0 && System.nanoTime() - retryBlockedUntilNanos.get() < 0) {
            // đang chờ nối lại sau lỗi hạ tầng: không thử DB nữa, không ack; broker sẽ gửi lại sau khi nối lại
            scheduleRestart();
            return;
        }
        MqttMessageProcessor.Outcome outcome = processor.process(topic, message.getPayload());
        log.debug("Kết quả xử lý id={}: {}", message.getId(), outcome);
        if (outcome == MqttMessageProcessor.Outcome.RETRY) {
            // khoảng chặn bao trùm thời gian ngắt, nối lại và nhận lại bản tin
            long window = TimeUnit.SECONDS.toNanos(props.restartDelaySeconds() + 2L);
            retryBlockedUntilNanos.set(System.nanoTime() + window);
            scheduleRestart(); // không ack: broker gửi lại khi nối lại
            return;
        }
        try {
            client.messageArrivedComplete(message.getId(), message.getQos());
            log.debug("Đã ack id={}", message.getId());
        } catch (MqttException e) {
            // không ack được (đang mất kết nối): broker sẽ gửi lại, DB chặn trùng theo event_id
            log.warn("Không ack được bản tin trên {}: {}", topic, e.getMessage());
        }
    }

    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
        // backend không publish ở phần này
    }
}
