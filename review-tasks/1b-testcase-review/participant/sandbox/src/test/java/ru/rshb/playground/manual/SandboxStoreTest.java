package ru.rshb.playground.manual;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.time.LocalDate;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class SandboxStoreTest {
    SandboxStore store;
    Model.User oper;
    Model.User controller;
    @BeforeEach void setup() {
        store = new SandboxStore(LocalDate.of(2026, 11, 5));
        oper = store.authenticate("tst_oper01", "Test123!");
        controller = store.authenticate("tst_contr01", "Test123!");
    }
    Map<String,Object> call(String action, Object... values) { return store.dispatch(oper, action, map(values)); }
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0; i<values.length; i+=2) result.put(values[i].toString(), values[i+1]);
        return result;
    }
    String client(Object... extra) {
        Map<String,Object> data = map("entity", "client", "surname", "Тестов", "name", "Иван", "patronymic", "Иванович",
            "birthDate", "1990-01-01", "passport", "4500123456", "fatca", "NON_US", "dbo", "FULL");
        data.putAll(map(extra));
        return store.dispatch(oper, "prepare", data).get("id").toString();
    }
    Map<String,Object> opening(String id, String amount) {
        return call("open-deposit", "clientId", id, "kind", "Пополняемый", "amount", amount,
            "term", "181", "funding", "Наличными через кассу", "interestPayment", "Капитализация");
    }
    Map<String,Object> sign(String id) {
        call("update-operation", "id", id, "bankOfficer", oper.fullName());
        call("print", "id", id);
        return call("sign", "id", id);
    }
    @Test void allRolesAuthenticateAndWrongPasswordFails() {
        for (String login: List.of("tst_oper01", "tst_fk01", "tst_kmtp01", "tst_contr01"))
            assertEquals(login, store.authenticate(login, "Test123!").login());
        assertThrows(Model.Problem.class, () -> store.authenticate("tst_oper01", "wrong"));
    }
    @Test void roleAndAgeCannotBeBypassed() {
        String id = client("birthDate", "2008-11-06");
        assertThrows(Model.Problem.class, () -> opening(id, "1000"));
        String adult = client("passport", "4500123457", "birthDate", "2008-11-05");
        assertNotNull(opening(adult, "1000").get("id"));
        Model.User manager = store.authenticate("tst_kmtp01", "Test123!");
        assertThrows(Model.Problem.class, () -> store.dispatch(manager, "open-deposit", map("clientId", adult)));
    }
    @Test void exactMinimumAcceptedAndBelowRejectedForEveryProduct() {
        String id = client();
        for (String[] row : new String[][]{{"Надёжный","9999.99","10000"},{"Пополняемый","999.99","1000"},{"До востребования","9.99","10"}}) {
            Map<String,Object> input = map("clientId", id, "kind", row[0], "amount", row[1], "term", "181", "funding", "Наличными через кассу");
            assertThrows(Model.Problem.class, () -> store.dispatch(oper,"open-deposit",input));
            input.put("amount",row[2]);
            assertNotNull(store.dispatch(oper,"open-deposit",input).get("id"));
        }
    }
    @Test void millionBoundaryAndApprovalDoNotDuplicateDeposit() {
        String id = client();
        String small = opening(id,"1000000").get("id").toString();
        assertEquals("Исполнена", sign(small).get("status"));
        String large = opening(id,"1000000.01").get("id").toString();
        assertEquals("На подтверждении", sign(large).get("status"));
        store.dispatch(controller,"take",map("id",large));
        assertEquals("Исполнена",store.dispatch(controller,"decide",map("id",large,"approve",true)).get("status"));
        assertThrows(Model.Problem.class, () -> store.dispatch(controller,"decide",map("id",large,"approve",true)));
        assertThrows(Model.Problem.class, () -> sign(small));
        assertEquals(2, ((List<?>)call("client","id",id).get("deposits")).size());
    }
    @Test void usResidentAlwaysNeedsControlAndRejectionNeedsComment() {
        String id=client("fatca","US");
        String op=opening(id,"1000").get("id").toString();
        assertEquals("На подтверждении",sign(op).get("status"));
        store.dispatch(controller,"take",map("id",op));
        assertThrows(Model.Problem.class, () -> store.dispatch(controller,"decide",map("id",op,"approve",false)));
        assertEquals("Отклонена",store.dispatch(controller,"decide",map("id",op,"approve",false,"comment","Отказ клиента")).get("status"));
        assertEquals(0,((List<?>)call("client","id",id).get("deposits")).size());
    }
    @Test void signingRequiresPrintingAndOfficer() {
        String op=opening(client(),"1000").get("id").toString();
        assertThrows(Model.Problem.class,()->call("sign","id",op));
        assertThrows(Model.Problem.class,()->call("print","id",op));
        call("update-operation","id",op,"bankOfficer","Тестов");
        call("print","id",op);
        assertEquals("Исполнена",call("sign","id",op).get("status"));
    }
    @Test void badAmountsAndDatesDoNotCreateEntities() {
        String id=client();
        for(String value:List.of("-1","NaN","1.001","")) assertThrows(Model.Problem.class,()->opening(id,value));
        assertThrows(Model.Problem.class,()->client("passport","123","birthDate","2026-02-30"));
    }
    String account(String client, String balance, String kind) {
        return call("prepare","entity","product","clientId",client,"type","account","kind",kind,"amount",balance).get("id").toString();
    }
    String deposit(String client,String sum,String opened,String kind) {
        return call("prepare","entity","product","clientId",client,"type","deposit","kind",kind,"amount",sum,"opened",opened,"term","181").get("id").toString();
    }
    Map<String,Object> form(Object... extra) {
        Map<String,Object> f=map("surname","Новый","name","Иван","patronymic","Иванович","birthDate","1991-01-01","passport","4500999999",
            "gender","Мужской","issued","2015-01-01","division","770-001","issuer","МВД","phone","+79001112233","address","Москва","citizenship","РФ");
        f.putAll(map(extra)); return f;
    }
    @Test void balanceFailurePrecedesMinorAndDboAndCardCannotClose() {
        String c=client("dbo","NONE","birthDate","2010-01-01");
        String a=account(c,"0.01","Текущий");
        Model.Problem error=assertThrows(Model.Problem.class,()->call("begin-close","productId",a));
        assertTrue(error.getMessage().contains("0,01 ₽"));
        assertThrows(Model.Problem.class,()->call("begin-close","productId",account(c,"0","Карточный")));
    }
    @Test void paperAccountClosesWithoutController() {
        String c=client("dbo","NONE"); String a=account(c,"0","Текущий");
        Map<String,Object> op=call("begin-close","productId",a);
        assertEquals(Messages.DBO,op.get("message"));
        call("update-operation","id",op.get("id"),"continuePaper",true);
        assertEquals("Исполнена",sign(op.get("id").toString()).get("status"));
        assertEquals("Закрыт",((Map<?,?>)((List<?>)call("client","id",c).get("accounts")).get(0)).get("status"));
    }
    @Test void earlyDepositPaysExactInterestOnceAfterControl() {
        String c=client("dbo","NONE"); String a=account(c,"5000","Текущий");
        String d=deposit(c,"100000","2026-10-06","Надёжный");
        Map<String,Object> op=call("begin-close","productId",d);
        assertEquals("100000.82",((Map<?,?>)op.get("fields")).get("payout"));
        call("update-operation","id",op.get("id"),"continuePaper",true,"targetId",a);
        assertEquals("На подтверждении",sign(op.get("id").toString()).get("status"));
        store.dispatch(controller,"take",map("id",op.get("id")));
        store.dispatch(controller,"decide",map("id",op.get("id"),"approve",true));
        assertEquals("105000.82",store.product(a).amount.toPlainString());
        assertThrows(Model.Problem.class,()->store.dispatch(controller,"decide",map("id",op.get("id"),"approve",true)));
        String second=deposit(c,"50000","2026-08-24","Пополняемый");
        assertEquals("50001.00",((Map<?,?>)call("begin-close","productId",second).get("fields")).get("payout"));
    }
    @Test void electronicThreeAttemptsCancelAndCannotBeResetByResending() {
        String c=client(); String a=account(c,"0","Текущий");
        String id=call("begin-close","productId",a).get("id").toString();
        call("send-sms","id",id);
        assertEquals(2,call("sign","id",id,"code","000000").get("attempts"));
        call("send-sms","id",id);
        assertEquals(1,call("sign","id",id,"code","000000").get("attempts"));
        assertEquals("Отменена",call("sign","id",id,"code","000000").get("status"));
        assertEquals("Открыт",store.product(a).status);
        assertThrows(Model.Problem.class,()->call("send-sms","id",id));
    }
    @Test void minorNeedsExistingRepresentativeAndCannotUseElectronicSigning() {
        String c=client("birthDate","2010-01-01"); String adult=client("passport","4500888888");
        String a=account(c,"0","Текущий"), d=deposit(c,"1000","2026-10-06","До востребования");
        Map<String,Object> op=call("begin-close","productId",d);
        assertEquals(Messages.MINOR,op.get("message")); assertEquals("Бумажное",op.get("signing"));
        assertThrows(Model.Problem.class,()->call("update-operation","id",op.get("id"),"signing","Электронное"));
        call("update-operation","id",op.get("id"),"targetId",a,"bankOfficer","Ирина");
        assertThrows(Model.Problem.class,()->call("print","id",op.get("id")));
        call("update-operation","id",op.get("id"),"representativeId",adult);
        assertEquals("На подтверждении",sign(op.get("id").toString()).get("status"));
    }
    @Test void currentRubleAccountRequiredAndOtherClientsAccountRejected() {
        String c=client(),other=client("passport","4500888888"); String foreign=account(other,"0","Текущий");
        String d=deposit(c,"1000","2026-10-06","До востребования");
        assertEquals(Messages.NO_ACCOUNT,assertThrows(Model.Problem.class,()->call("begin-close","productId",d)).getMessage());
        account(c,"0","Текущий"); String id=call("begin-close","productId",d).get("id").toString();
        assertThrows(Model.Problem.class,()->call("update-operation","id",id,"targetId",foreign));
    }
    @Test void fourteenBoundaryAndPassportDuplicateStopFurtherChecks() {
        assertEquals(Messages.AGE,assertThrows(Model.Problem.class,()->store.dispatch(oper,"create-client",form("birthDate","2012-11-06"))).getMessage());
        assertEquals("Исполнена",store.dispatch(oper,"create-client",form("birthDate","2012-11-05")).get("status"));
        assertEquals(Messages.PASSPORT,store.dispatch(oper,"create-client",form("fmList","Решения межведомственной комиссии")).get("message"));
    }
    @Test void nameNormalizationAndPatronymicDifference() {
        client("surname","Семёнова","name","Алёна","patronymic","Игоревна");
        Map<String,Object> duplicate=store.dispatch(oper,"create-client",form("surname","СЕМЕНОВА","name","АЛЕНА","patronymic","ИГОРЕВНА","birthDate","1990-01-01"));
        assertEquals("DUPLICATE",duplicate.get("stage"));
        assertEquals("Исполнена",store.dispatch(oper,"create-client",form("passport","4500999998","surname","СЕМЕНОВА","name","АЛЕНА","patronymic","","birthDate","1990-01-01")).get("status"));
    }
    @Test void previousPassportFindsExistingWithoutCreatingAnother() {
        String old=client("previousPassports","4500444444");
        Map<String,Object> op=store.dispatch(oper,"create-client",form("surname","Тестов","birthDate","1990-01-01"));
        Map<String,Object> found=call("continue-client","id",op.get("id"),"choice","previous","passport","4500444444");
        assertEquals(Messages.PREVIOUS,found.get("message")); assertEquals(old,found.get("existingId"));
        assertThrows(Model.Problem.class,()->call("search","passport","4500999999"));
    }
    @Test void financialMonitoringPrecedesControlAndDraftInvisibleUntilApproval() {
        client();
        Map<String,Object> op=store.dispatch(oper,"create-client",form("surname","Тестов","birthDate","1990-01-01","fmList","Решения межведомственной комиссии"));
        op=call("continue-client","id",op.get("id"),"choice","noPrevious");
        assertEquals("FINMON",op.get("stage")); assertEquals("Черновик",op.get("status"));
        op=call("continue-client","id",op.get("id"),"choice","continue");
        assertEquals("На подтверждении",op.get("status"));
        assertThrows(Model.Problem.class,()->call("search","passport","4500999999"));
        final Object id=op.get("id");
        Model.User wrong=store.authenticate("tst_contr02","Test123!");
        assertThrows(Model.Problem.class,()->store.dispatch(wrong,"take",map("id",id)));
        store.dispatch(controller,"take",map("id",id));
        store.dispatch(controller,"decide",map("id",id,"approve",true));
        assertTrue(((List<?>)call("search","passport","4500999999").get("history")).contains("Передано в финмониторинг"));
    }
    @Test void cancellingClientControlDeletesDraftAndRequiresComment() {
        client();
        Map<String,Object> op=store.dispatch(oper,"create-client",form("surname","Тестов","birthDate","1990-01-01"));
        op=call("continue-client","id",op.get("id"),"choice","noPrevious");
        Object id=op.get("id"); store.dispatch(controller,"take",map("id",id));
        assertThrows(Model.Problem.class,()->store.dispatch(controller,"decide",map("id",id,"approve",false)));
        assertEquals("Отменена",store.dispatch(controller,"decide",map("id",id,"approve",false,"comment","Дубль")).get("status"));
        assertThrows(Model.Problem.class,()->call("search","passport","4500999999"));
    }
    @Test void savingUnchangedElectronicChoicePreservesSentCode() {
        String c=client(); String a=account(c,"0","Текущий");
        String id=call("begin-close","productId",a).get("id").toString();
        call("send-sms","id",id);
        var messages=(List<?>)call("sms").get("messages");
        String code=((Map<?,?>)messages.get(messages.size()-1)).get("code").toString();
        call("update-operation","id",id,"signing","Электронное");
        assertEquals("Исполнена",call("sign","id",id,"code",code).get("status"));
    }
    @Test void invalidPreparationDoesNotPartiallyChangeExistingClient() {
        String c=client();
        assertThrows(Model.Problem.class,()->client("id",c,"surname","Изменён","previousPassports","bad"));
        assertEquals("Тестов",call("client","id",c).get("surname"));
    }
    @Test void resetDoesNotReuseOperationAddressesFromPreviousRun() {
        String old=opening(client(),"1000").get("id").toString();
        store.reset();
        String fresh=opening(client(),"1000").get("id").toString();
        assertNotEquals(old,fresh);
        assertThrows(Model.Problem.class,()->call("operation","id",old));
    }
}
