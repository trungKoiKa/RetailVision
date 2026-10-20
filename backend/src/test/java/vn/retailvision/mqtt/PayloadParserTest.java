package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import jakarta.validation.Validation;
import java.util.List;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestFactory;
import vn.retailvision.dto.mqtt.AlertMessage;
import vn.retailvision.dto.mqtt.CrossingMessage;
import vn.retailvision.dto.mqtt.StateMessage;
import vn.retailvision.dto.mqtt.StatusMessage;
import vn.retailvision.dto.mqtt.TelemetryMessage;
import vn.retailvision.exception.InvalidPayloadException;
import vn.retailvision.support.ContractExamples;
import vn.retailvision.support.ContractExamples.Example;

/** Backend phải chấp nhận mọi ví dụ hợp lệ và từ chối mọi ví dụ sai trong contracts/examples. */
class PayloadParserTest {

    private static final List<String> PREFIXES = List.of("state", "crossing", "alert", "telemetry", "status");

    private final PayloadParser parser =
            new PayloadParser(Validation.buildDefaultValidatorFactory().getValidator());

    private static Class<?> typeFor(String prefix) {
        return switch (prefix) {
            case "state" -> StateMessage.class;
            case "crossing" -> CrossingMessage.class;
            case "alert" -> AlertMessage.class;
            case "telemetry" -> TelemetryMessage.class;
            case "status" -> StatusMessage.class;
            default -> throw new IllegalArgumentException(prefix);
        };
    }

    @TestFactory
    List<DynamicTest> everyValidExampleIsAccepted() {
        List<Example> examples = ContractExamples.valid(PREFIXES.toArray(String[]::new));
        assertThat(examples).hasSizeGreaterThanOrEqualTo(8);
        return examples.stream()
                .map(e -> DynamicTest.dynamicTest("valid/" + e.name(), () -> assertThat(parser.parse(e.bytes(), typeFor(e.prefix()))).isNotNull()))
                .toList();
    }

    @TestFactory
    List<DynamicTest> everyInvalidExampleIsRejected() {
        List<Example> examples = ContractExamples.invalid(PREFIXES.toArray(String[]::new));
        assertThat(examples).hasSizeGreaterThanOrEqualTo(8);
        return examples.stream()
                .map(e -> DynamicTest.dynamicTest("invalid/" + e.name(), () ->
                        assertThatThrownBy(() -> parser.parse(e.bytes(), typeFor(e.prefix())))
                                .isInstanceOf(InvalidPayloadException.class)))
                .toList();
    }

    @Test
    void unknownStateAllowsNullQueueCountAndKeepsItNull() {
        var m = parser.parse(ContractExamples.validBytes("state__unknown.json"), StateMessage.class);
        assertThat(m.state()).isEqualTo("UNKNOWN");
        assertThat(m.queueCount()).isNull(); // null, không phải 0
    }

    @Test
    void ackedAlertCarriesAckIds() {
        var m = parser.parse(ContractExamples.validBytes("alert__ack.json"), AlertMessage.class);
        assertThat(m.transition()).isEqualTo("ACK");
        assertThat(m.ackId()).isNotNull();
        assertThat(m.ackDeviceId()).isEqualTo("node01");
    }

    @Test
    void emptyOversizedAndGarbagePayloadsAreRejected() {
        assertThatThrownBy(() -> parser.parse(new byte[0], StateMessage.class)).isInstanceOf(InvalidPayloadException.class);
        assertThatThrownBy(() -> parser.parse(new byte[20_000], StateMessage.class)).isInstanceOf(InvalidPayloadException.class);
        assertThatThrownBy(() -> parser.parse("not json".getBytes(), StateMessage.class)).isInstanceOf(InvalidPayloadException.class);
        assertThatThrownBy(() -> parser.parse("[]".getBytes(), StateMessage.class)).isInstanceOf(InvalidPayloadException.class);
        assertThatThrownBy(() -> parser.parse("{}".getBytes(), StateMessage.class)).isInstanceOf(InvalidPayloadException.class);
    }

    @Test
    void trailingContentAfterJsonIsRejected() {
        String valid = ContractExamples.text(ContractExamples.validBytes("crossing__in.json"));
        assertThatThrownBy(() -> parser.parse((valid + " {}").getBytes(), CrossingMessage.class))
                .isInstanceOf(InvalidPayloadException.class);
    }
}
