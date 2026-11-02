package ru.rshb.playground.manual;

import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.Locale;

public final class Messages {
    private Messages() { }
    public static final String FATCA = "Операция недоступна: у клиента не определён FATCA-статус. Заполните форму самосертификации.";
    public static final String US = "Клиент является налоговым резидентом США. Заявка будет направлена на подтверждение контролёру.";
    public static final String CONTROL = "Заявка направлена на подтверждение контролёру";
    public static final String NO_ACCOUNT = "У клиента нет открытого текущего счёта в рублях. Откройте счёт, чтобы перечислить средства вклада.";
    public static final String EARLY = "Вклад закрывается досрочно. Проценты будут пересчитаны по ставке 0,01% годовых.";
    public static final String DBO = "У клиента нет полного доступа в ДБО. Электронное подписание недоступно.";
    public static final String MINOR = "Клиенту меньше 18 лет. Операция проводится с участием законного представителя.";
    public static final String EXHAUSTED = "Попытки исчерпаны. Операция отменена.";
    public static final String AGE = "Клиенту меньше 14 лет. Создание клиента по паспорту РФ невозможно.";
    public static final String PASSPORT = "Клиент с таким паспортом уже существует";
    public static final String DUPLICATE = "Клиент с такими ФИО и датой рождения уже есть в системе. Укажите данные предыдущего паспорта РФ, чтобы не создать дубль карточки.";
    public static final String PREVIOUS = "Найден клиент с этим паспортом. Обновите паспорт в карточке существующего клиента.";
    public static final String SAVED = "Карточка клиента сохранена";
    public static final String CLIENT_CONTROL = "Операция требует подтверждения контролирующим работником";
    public static final String WARNING = "Возможен дубль клиента. Проверьте данные в АБС перед подтверждением.";
    public static String fm(String list) {
        return "Выявлено совпадение данных клиента со списком: " + list + ". Вы можете продолжить операцию. Информация будет передана в финмониторинг.";
    }
    public static String money(BigDecimal amount) {
        DecimalFormatSymbols symbols = DecimalFormatSymbols.getInstance(Locale.forLanguageTag("ru-RU"));
        symbols.setGroupingSeparator(' ');
        return new DecimalFormat("#,##0.00", symbols).format(amount);
    }
}
