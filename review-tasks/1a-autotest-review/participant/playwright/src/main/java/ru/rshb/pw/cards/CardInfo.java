package ru.rshb.pw.cards;

/**
 * Данные выпуска карты из API.
 */
public record CardInfo(String cardNumber, String holderName, String expiry, String accountNumber, String status) {
}
