package ru.rshb.entities;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Getter;
import ru.rshb.utils.YamlReader;

/**
 * Стенд ЕФР. Адреса читаются из yaml-файла по имени стенда.
 */
@Getter
public class Stand {

    private String name;
    private String newEfrApplicationUrl;
    private String efrApiUrl;

    public void get(String standName, String fileName) {
        JsonNode node = YamlReader.read(fileName).get(standName);
        if (node == null) {
            throw new IllegalArgumentException("Стенд '%s' не найден в %s".formatted(standName, fileName));
        }
        this.name = standName;
        this.newEfrApplicationUrl = node.get("newEfrApplicationUrl").asText();
        this.efrApiUrl = node.get("efrApiUrl").asText();
    }
}
