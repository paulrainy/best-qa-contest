package ru.rshb.entities.efr_client;

import lombok.Data;

/**
 * Клиент ЕФР, созданный через API.
 */
@Data
public class EfrClient {

    private String clientId;
    private String fullName;
    private String phone;
    private String passportSeries;
    private String passportNumber;
}
