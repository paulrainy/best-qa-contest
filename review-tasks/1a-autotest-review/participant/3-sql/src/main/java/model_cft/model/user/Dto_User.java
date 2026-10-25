package model_cft.model.user;

import model_cft.model.Rows;

import java.util.Map;

/**
 * Пользователь ЦФТ — строка Z#USER.
 */
public class Dto_User {

    private final Long id;
    private final String login;
    private final String name;
    private final String filial;
    private final Long depart;

    Dto_User(Map<String, Object> row) {
        this.id = Rows.id(row, "ID");
        this.login = Rows.text(row, "C_LOGIN");
        this.name = Rows.text(row, "C_NAME");
        this.filial = Rows.text(row, "C_FILIAL");
        this.depart = Rows.id(row, "C_DEPART");
    }

    public Long getId() {
        return id;
    }

    public String getLogin() {
        return login;
    }

    public String getName() {
        return name;
    }

    public String getFilial() {
        return filial;
    }

    public Long getDepart() {
        return depart;
    }

    @Override
    public String toString() {
        return "пользователь %s (%s)".formatted(login, name);
    }
}
