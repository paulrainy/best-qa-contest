package ru.rshb.pages.cards;

/**
 * Карточка карты в продуктовом профиле клиента.
 */
public class CardProfilePage {

    private static final String CARD = "//div[@data-id='cardProfile']";
    private static final String DIALOG = "//div[@role='dialog']";
    private static final String MENU = "//div[@role='menu']";

    // Шапка карточки
    public String cardStatusXpath = CARD + "//span[@data-id='cardStatus']";
    public String blockReasonXpath = CARD + "//span[@data-id='blockReason']";
    public String blockButtonXpath = CARD + "//button[normalize-space()='Заблокировать']";
    public String unblockButtonXpath = CARD + "//button[normalize-space()='Разблокировать']";

    // Меню «Действия»
    public String actionsMenuXpath = CARD + "//button[normalize-space()='Действия']";
    public String reissueItemXpath = MENU + "//div[@role='menuitem' and normalize-space()='Перевыпустить']";
    public String changePinItemXpath = MENU + "//div[@role='menuitem' and normalize-space()='Сменить ПИН-код']";
    public String tooltipXpath = "//div[@role='tooltip']";

    // Окна подтверждения
    public String blockDialogXpath = DIALOG + "[@data-id='blockDialog']";
    public String blockReasonSelectXpath = DIALOG + "//select[@name='blockReason']";
    public String reissueReasonSelectXpath = DIALOG + "//select[@name='reissueReason']";
    public String supervisorLoginXpath = DIALOG + "//input[@name='supervisorLogin']";
    public String supervisorPasswordXpath = DIALOG + "//input[@name='supervisorPassword']";
    public String confirmButtonXpath = DIALOG + "//button[normalize-space()='Подтвердить']";
    public String cancelButtonXpath = DIALOG + "//button[normalize-space()='Отмена']";

    // Уведомления
    public String notificationXpath = "//div[@data-id='notification']";
    public String successNotificationXpath = "//div[@data-id='notification' and contains(@class, 'success')]";

    // Вкладка «Лимиты»
    public String limitsTabXpath = CARD + "//div[@role='tab' and normalize-space()='Лимиты']";
    public String cashLimitInputXpath = CARD + "//input[@name='cashLimit']";
    public String onlineLimitInputXpath = CARD + "//input[@name='onlineLimit']";
    public String saveButtonXpath = CARD + "//button[normalize-space()='Сохранить']";

    // Вкладка «История»
    public String historyTabXpath = CARD + "//div[@role='tab' and normalize-space()='История']";
    public String historyRowXpath = CARD + "//table[@data-id='history']//tr[@data-id='historyRow']";

    // Вкладка «Реквизиты»
    public String requisiteCardNumberXpath = CARD + "//dd[@data-id='requisiteCardNumber']";
    public String requisiteHolderXpath = CARD + "//dd[@data-id='requisiteHolder']";
    public String requisiteExpiryXpath = CARD + "//dd[@data-id='requisiteExpiry']";
    public String requisiteAccountXpath = CARD + "//dd[@data-id='requisiteAccount']";
}
