package ru.rshb.entities;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Getter;
import lombok.Setter;
import ru.rshb.utils.YamlReader;

/**
 * Пользователь ЕФР. Логин и пароль читаются из yaml-файла по имени роли.
 */
@Getter
@Setter
public class WebUser {

    private String role;
    private String login;
    private String password;

    public void get(String roleName, String fileName) {
        JsonNode node = YamlReader.read(fileName).get(roleName);
        if (node == null) {
            throw new IllegalArgumentException("Роль '%s' не найдена в %s".formatted(roleName, fileName));
        }
        this.role = roleName;
        this.login = node.get("login").asText();
        this.password = node.get("password").asText();
    }
}
