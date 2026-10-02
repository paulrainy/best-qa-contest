package ru.rshb.entities.cards;

import lombok.Data;

/**
 * Данные выпуска карты из процессинга.
 */
@Data
public class CardInfo {

    private String cardNumber;
    private String holderName;
    private String expiry;
    private String accountNumber;
    private String status;
}
