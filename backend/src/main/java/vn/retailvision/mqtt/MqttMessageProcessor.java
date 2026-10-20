package vn.retailvision.mqtt;

import java.sql.SQLRecoverableException;
import java.sql.SQLTransientException;
import java.net.ConnectException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.TransientDataAccessException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.CannotCreateTransactionException;
import vn.retailvision.exception.InvalidPayloadException;

/**
 * Quyết định số phận một bản tin sau khi xử lý, tách khỏi Paho để test được.
 *
 * <ul>
 *   <li>ACK: đã ghi xong (đã commit), hoặc bản tin sai nên bỏ, hoặc lỗi chắc chắn lặp lại
 *       (không có ích khi gửi lại) đã ghi log lỗi.
 *   <li>RETRY: lỗi hạ tầng tạm thời (DB tắt, mất kết nối...). Không ack để broker gửi lại.
 * </ul>
 */
@Component
public class MqttMessageProcessor {

    public enum Outcome {
        ACK,
        RETRY
    }

    private static final Logger log = LoggerFactory.getLogger(MqttMessageProcessor.class);

    private final MqttRouter router;

    public MqttMessageProcessor(MqttRouter router) {
        this.router = router;
    }

    public Outcome process(String topic, byte[] payload) {
        try {
            router.handle(topic, payload);
            return Outcome.ACK;
        } catch (InvalidPayloadException e) {
            log.warn("Bỏ bản tin sai trên {}: {}", topic, e.getMessage());
            return Outcome.ACK;
        } catch (RuntimeException e) {
            if (isTransient(e)) {
                log.error("Lỗi hạ tầng khi xử lý bản tin trên {}; không ack để broker gửi lại", topic, e);
                return Outcome.RETRY;
            }
            // lỗi lặp lại mãi với cùng bản tin (ví dụ vi phạm ràng buộc): gửi lại chỉ gây vòng lặp vô hạn
            log.error("Bỏ bản tin trên {} vì lỗi không thể khắc phục bằng gửi lại", topic, e);
            return Outcome.ACK;
        }
    }

    static boolean isTransient(Throwable error) {
        for (Throwable t = error; t != null; t = t.getCause()) {
            if (t instanceof TransientDataAccessException
                    || t instanceof DataAccessResourceFailureException
                    || t instanceof CannotCreateTransactionException
                    || t instanceof SQLTransientException
                    || t instanceof SQLRecoverableException
                    || t instanceof ConnectException) {
                return true;
            }
            if (t.getCause() == t) {
                break;
            }
        }
        return false;
    }
}
