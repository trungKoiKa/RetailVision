package vn.retailvision.mqtt;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validator;
import java.nio.charset.StandardCharsets;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;
import vn.retailvision.exception.InvalidPayloadException;

/**
 * Đổi payload JSON thành DTO và kiểm theo contract: trường lạ, thiếu trường bắt buộc, sai kiểu,
 * sai enum hoặc ngoài khoảng đều bị từ chối.
 */
@Component
public class PayloadParser {

    private static final int MAX_BYTES = 16 * 1024;

    private final ObjectMapper mapper = JsonMapper.builder()
            .addModule(new JavaTimeModule())
            .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
            .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .enable(DeserializationFeature.FAIL_ON_NULL_FOR_PRIMITIVES)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
            .build();

    private final Validator validator;

    public PayloadParser(Validator validator) {
        this.validator = validator;
    }

    public <T> T parse(byte[] raw, Class<T> type) {
        if (raw == null || raw.length == 0) {
            throw new InvalidPayloadException("payload rỗng");
        }
        if (raw.length > MAX_BYTES) {
            throw new InvalidPayloadException("payload quá lớn: " + raw.length + " byte");
        }
        T value;
        try {
            value = mapper.readValue(new String(raw, StandardCharsets.UTF_8), type);
        } catch (JsonProcessingException e) {
            throw new InvalidPayloadException("JSON không hợp lệ: " + e.getOriginalMessage(), e);
        }
        Set<ConstraintViolation<T>> violations = validator.validate(value);
        if (!violations.isEmpty()) {
            String detail = violations.stream()
                    .map(v -> v.getPropertyPath() + " " + v.getMessage())
                    .sorted()
                    .collect(Collectors.joining("; "));
            throw new InvalidPayloadException("sai contract: " + detail);
        }
        return value;
    }
}
