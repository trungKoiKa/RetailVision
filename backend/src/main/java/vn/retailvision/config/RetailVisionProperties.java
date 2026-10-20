package vn.retailvision.config;

import java.time.ZoneId;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** Cấu hình ứng dụng, đọc từ prefix `retailvision` trong application.yml. */
@ConfigurationProperties(prefix = "retailvision")
public record RetailVisionProperties(
        @DefaultValue("Asia/Ho_Chi_Minh") ZoneId timezone,
        @DefaultValue("5") int staleSeconds,
        Mqtt mqtt) {

    public record Mqtt(
            @DefaultValue("true") boolean enabled,
            @DefaultValue("127.0.0.1") String host,
            @DefaultValue("1883") int port,
            String username,
            String password,
            @DefaultValue("backend01") String clientId,
            @DefaultValue("site01") String siteId,
            @DefaultValue("edge01") String edgeId,
            @DefaultValue("node01") String nodeId,
            @DefaultValue("5") int restartDelaySeconds) {

        /** Tiền tố topic: retailvision/v1/{site}/ */
        public String topicPrefix() {
            return "retailvision/v1/" + siteId + "/";
        }
    }
}
