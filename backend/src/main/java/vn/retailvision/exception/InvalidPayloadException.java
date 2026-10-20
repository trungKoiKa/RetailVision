package vn.retailvision.exception;

/** Bản tin MQTT sai định dạng hoặc sai contract. Bị bỏ và ghi log, không thử lại. */
public class InvalidPayloadException extends RuntimeException {

    public InvalidPayloadException(String message) {
        super(message);
    }

    public InvalidPayloadException(String message, Throwable cause) {
        super(message, cause);
    }
}
