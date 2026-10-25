package ru.rshb.utils;

public class GeneralUtil {

    /**
     * Значение из системного свойства или, если его нет, из переменной окружения.
     */
    public String getEnvironmentVariable(String name) {
        String value = System.getProperty(name);
        if (value == null) {
            value = System.getenv(name);
        }
        if (value == null) {
            throw new IllegalStateException("Не задана переменная окружения " + name);
        }
        return value;
    }
}
