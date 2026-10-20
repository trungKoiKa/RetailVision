package vn.retailvision.mqtt;

import org.springframework.stereotype.Component;
import vn.retailvision.config.RetailVisionProperties;
import vn.retailvision.dto.mqtt.AlertMessage;
import vn.retailvision.dto.mqtt.CrossingMessage;
import vn.retailvision.dto.mqtt.EnvelopeMessage;
import vn.retailvision.dto.mqtt.SettingsResultMessage;
import vn.retailvision.dto.mqtt.StateMessage;
import vn.retailvision.dto.mqtt.StatusMessage;
import vn.retailvision.dto.mqtt.TelemetryMessage;
import vn.retailvision.exception.InvalidPayloadException;
import vn.retailvision.service.ingestion.IngestionService;
import vn.retailvision.service.queue.LiveStateCache;
import vn.retailvision.service.settings.SettingsService;

/**
 * Chuyển bản tin theo topic tới đúng xử lý. Kiểm thêm site_id/device_id trong payload khớp topic
 * để một thiết bị không giả mạo bản tin của thiết bị khác.
 *
 * Ném InvalidPayloadException cho bản tin sai (bỏ). Mọi lỗi khác (ví dụ lỗi DB) cho lan ra để
 * listener không ack và broker gửi lại.
 */
@Component
public class MqttRouter {

    private final PayloadParser parser;
    private final IngestionService ingestion;
    private final LiveStateCache live;
    private final SettingsService settings;
    private final RetailVisionProperties.Mqtt mqtt;

    public MqttRouter(
            PayloadParser parser,
            IngestionService ingestion,
            LiveStateCache live,
            SettingsService settings,
            RetailVisionProperties props) {
        this.parser = parser;
        this.ingestion = ingestion;
        this.live = live;
        this.settings = settings;
        this.mqtt = props.mqtt();
    }

    /** Danh sách topic cần đăng ký và QoS của đăng ký. */
    public String[] subscriptionTopics() {
        String p = mqtt.topicPrefix();
        return new String[] {
            p + mqtt.edgeId() + "/state",
            p + mqtt.edgeId() + "/events/crossing",
            p + mqtt.edgeId() + "/events/alert",
            p + mqtt.edgeId() + "/telemetry",
            p + mqtt.edgeId() + "/status",
            p + mqtt.nodeId() + "/status",
            p + mqtt.edgeId() + "/settings/result"
        };
    }

    public int[] subscriptionQos() {
        return new int[] {0, 1, 1, 1, 1, 1, 1};
    }

    public void handle(String topic, byte[] payload) {
        String prefix = mqtt.topicPrefix();
        if (!topic.startsWith(prefix)) {
            throw new InvalidPayloadException("topic ngoài site: " + topic);
        }
        String rest = topic.substring(prefix.length());
        String edge = mqtt.edgeId();
        String node = mqtt.nodeId();

        if (rest.equals(edge + "/state")) {
            StateMessage m = parser.parse(payload, StateMessage.class);
            checkOrigin(m, edge);
            live.update(m);
        } else if (rest.equals(edge + "/events/crossing")) {
            CrossingMessage m = parser.parse(payload, CrossingMessage.class);
            checkOrigin(m, edge);
            ingestion.ingest(m);
        } else if (rest.equals(edge + "/events/alert")) {
            AlertMessage m = parser.parse(payload, AlertMessage.class);
            checkOrigin(m, edge);
            ingestion.ingest(m);
        } else if (rest.equals(edge + "/telemetry")) {
            TelemetryMessage m = parser.parse(payload, TelemetryMessage.class);
            checkOrigin(m, edge);
            ingestion.ingest(m);
        } else if (rest.equals(edge + "/status")) {
            StatusMessage m = parser.parse(payload, StatusMessage.class);
            checkOrigin(m, edge);
            ingestion.ingest(m);
        } else if (rest.equals(edge + "/settings/result")) {
            SettingsResultMessage m = parser.parse(payload, SettingsResultMessage.class);
            checkOrigin(m, edge);
            settings.onResult(m);
        } else if (rest.equals(node + "/status")) {
            StatusMessage m = parser.parse(payload, StatusMessage.class);
            checkOrigin(m, node);
            ingestion.ingest(m);
        } else {
            throw new InvalidPayloadException("topic không được hỗ trợ: " + topic);
        }
    }

    private void checkOrigin(EnvelopeMessage m, String expectedDevice) {
        if (!mqtt.siteId().equals(m.siteId())) {
            throw new InvalidPayloadException("site_id " + m.siteId() + " không khớp topic");
        }
        if (!expectedDevice.equals(m.deviceId())) {
            throw new InvalidPayloadException("device_id " + m.deviceId() + " không khớp topic");
        }
    }
}
