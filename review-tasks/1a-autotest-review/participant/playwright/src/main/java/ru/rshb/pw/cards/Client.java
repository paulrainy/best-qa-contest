package ru.rshb.pw.cards;

/**
 * Клиент, созданный через API.
 */
public record Client(String id, String fullName, String passportSeries, String passportNumber) {
}
