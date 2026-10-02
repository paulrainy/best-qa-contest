package ru.rshb.utils;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;

public final class YamlReader {

    private static final ObjectMapper YAML = new ObjectMapper(new YAMLFactory());

    private YamlReader() {
    }

    public static JsonNode read(String fileName) {
        try (InputStream in = YamlReader.class.getClassLoader().getResourceAsStream(fileName)) {
            if (in == null) {
                throw new IllegalArgumentException("Файл %s не найден в ресурсах".formatted(fileName));
            }
            return YAML.readTree(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
