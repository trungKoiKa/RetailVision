package vn.retailvision;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class RetailVisionApplication {

    public static void main(String[] args) {
        SpringApplication.run(RetailVisionApplication.class, args);
    }
}
