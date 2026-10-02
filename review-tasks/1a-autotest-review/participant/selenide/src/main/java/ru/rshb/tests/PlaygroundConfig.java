package ru.rshb.tests;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import ru.rshb.entities.Stand;
import ru.rshb.entities.WebUser;
import ru.rshb.utils.EfrApiProcessing;

@Configuration
public class PlaygroundConfig {

    @Bean
    public Stand stand() {
        return new Stand();
    }

    @Bean
    public WebUser webUser() {
        return new WebUser();
    }

    @Bean
    public EfrApiProcessing efrApiProcessing() {
        return new EfrApiProcessing();
    }
}
