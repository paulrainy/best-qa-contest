package ru.rshb.playground.manual;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

/** Объекты только учебной песочницы. Денежные значения не используют double. */
public final class Model {
    private Model() { }
    public enum Role { OPER, FK, MANAGER, CONTROLLER }
    public record User(String login, String fullName, Role role, String branch) { }
    public static class Problem extends RuntimeException {
        public final int status;
        public Problem(int status, String message) { super(message); this.status = status; }
    }
    static class Client {
        String id, surname, name, patronymic, passport, status = "Активен", fatca = "NON_US", dbo = "FULL";
        LocalDate birthDate;
        Map<String,Object> fields = new LinkedHashMap<>();
        List<String> previousPassports = new ArrayList<>();
        List<String> history = new ArrayList<>();
        String fullName() { return (surname + " " + name + " " + patronymic).trim(); }
    }
    static class Product {
        String id, clientId, type, kind, number, currency = "RUB", status = "Открыт";
        BigDecimal amount;
        LocalDate opened;
        int term;
    }
    static class Operation {
        String id, type, owner, branch, clientId, productId = "", status = "Черновик", stage = "PARAMETERS";
        String signing = "Бумажное", takenBy = "", message = "", duplicateId = "", smsCode = "";
        int attempts = 3;
        boolean printed, needsControl;
        Client candidate;
        Map<String,Object> fields = new LinkedHashMap<>();
    }
}
