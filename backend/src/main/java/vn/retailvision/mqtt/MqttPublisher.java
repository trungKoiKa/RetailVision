package vn.retailvision.mqtt;

/** Gửi bản tin lên broker. Chỉ có bean này khi MQTT được bật. */
public interface MqttPublisher {

    /** Ném {@link PublishFailedException} nếu chưa gửi được (ví dụ mất kết nối); không xếp hàng chờ. */
    void publish(String topic, byte[] payload, int qos, boolean retain);

    class PublishFailedException extends RuntimeException {
        public PublishFailedException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
