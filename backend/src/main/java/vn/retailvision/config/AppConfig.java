package vn.retailvision.config;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class AppConfig {

    /** Đồng hồ máy chủ; test thay bằng Clock cố định. */
    @Bean
    public Clock clock() {
        return Clock.systemUTC();
    }
}
