package vn.retailvision.mqtt;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;

import java.net.ConnectException;
import java.sql.SQLTransientConnectionException;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.transaction.CannotCreateTransactionException;
import vn.retailvision.exception.InvalidPayloadException;
import vn.retailvision.mqtt.MqttMessageProcessor.Outcome;

/** Quy tắc ack: chỉ ack khi đã ghi xong, hoặc bản tin sai/không cứu được; lỗi hạ tầng thì không ack. */
class MqttMessageProcessorTest {

    private final MqttRouter router = mock(MqttRouter.class);
    private final MqttMessageProcessor processor = new MqttMessageProcessor(router);
    private static final String TOPIC = "retailvision/v1/site01/edge01/events/crossing";

    @Test
    void successfulHandlingIsAcked() {
        assertThat(processor.process(TOPIC, new byte[] {1})).isEqualTo(Outcome.ACK);
    }

    @Test
    void invalidPayloadIsDroppedWithAck() {
        doThrow(new InvalidPayloadException("sai")).when(router).handle(TOPIC, new byte[] {1});
        assertThat(processor.process(TOPIC, new byte[] {1})).isEqualTo(Outcome.ACK);
    }

    @Test
    void databaseOutageIsNotAckedSoBrokerRedelivers() {
        doThrow(new DataAccessResourceFailureException("db down")).when(router).handle(TOPIC, new byte[] {1});
        assertThat(processor.process(TOPIC, new byte[] {1})).isEqualTo(Outcome.RETRY);
    }

    @Test
    void transientCausesAnywhereInTheChainAreRetried() {
        for (RuntimeException e : new RuntimeException[] {
            new CannotCreateTransactionException("không mở được transaction"),
            new CannotGetJdbcConnectionException("không có kết nối", new SQLTransientConnectionException("timeout")),
            new RuntimeException("bọc ngoài", new RuntimeException("giữa", new ConnectException("refused")))
        }) {
            doThrow(e).when(router).handle(TOPIC, new byte[] {1});
            assertThat(processor.process(TOPIC, new byte[] {1})).as(e.toString()).isEqualTo(Outcome.RETRY);
        }
    }

    @Test
    void permanentFailureIsAckedToAvoidAnEndlessRedeliveryLoop() {
        doThrow(new DataIntegrityViolationException("vi phạm ràng buộc")).when(router).handle(TOPIC, new byte[] {1});
        assertThat(processor.process(TOPIC, new byte[] {1})).isEqualTo(Outcome.ACK);
        doThrow(new IllegalStateException("bug")).when(router).handle(TOPIC, new byte[] {1});
        assertThat(processor.process(TOPIC, new byte[] {1})).isEqualTo(Outcome.ACK);
    }
}
