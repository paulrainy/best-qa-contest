package ru.rshb.playground.manual;

import static ru.rshb.playground.manual.Model.*;
import static ru.rshb.playground.manual.SandboxStore.*;
import java.util.*;

/** Последовательность проверок BIQ-90103; переходы подтверждаются отдельными действиями. */
final class ClientRegistration {
    private final SandboxStore s;
    ClientRegistration(SandboxStore store) { s=store; }
    Map<String,Object> create(User user,Map<String,Object> input) {
        require(user.role()==Role.OPER || user.role()==Role.MANAGER,403,"У роли нет права на создание клиента");
        for(String key:List.of("surname","name","birthDate","gender","passport","issued","division","issuer","phone","address")) require(!text(input,key).isEmpty(),400,"Заполните обязательное поле: "+key);
        require(value(input,"citizenship","РФ").equals("РФ"),400,"Гражданство РФ доступно только для чтения");
        Client c=new Client(); c.birthDate=date(text(input,"birthDate"));
        require(!c.birthDate.isAfter(s.today),400,"Дата рождения позже даты операции");
        require(!c.birthDate.plusYears(14).isAfter(s.today),400,Messages.AGE);
        c.passport=passport(text(input,"passport"));
        date(text(input,"issued"));
        require(text(input,"division").matches("\\d{3}-\\d{3}"),400,"Код подразделения: 000-000");
        c.surname=text(input,"surname"); c.name=text(input,"name"); c.patronymic=text(input,"patronymic"); c.fields.putAll(input);
        Optional<Client> passportMatch=s.clients.values().stream().filter(x->x.passport.equals(c.passport)).findFirst();
        if(passportMatch.isPresent()) {
            Client existing=passportMatch.get(); require(existing.status.equals("Активен"),409,"Создание клиента с этим паспортом уже на подтверждении");
            Operation op=s.operation(user,"CREATE_CLIENT",existing); op.stage="EXISTING"; op.status="Отменена"; op.message=Messages.PASSPORT; op.duplicateId=existing.id;
            s.operations.put(op.id,op); return s.operationView(op);
        }
        c.id=s.next("c"); c.status="Черновик";
        Operation op=s.operation(user,"CREATE_CLIENT",c); op.candidate=c;
        op.fields.putAll(input);
        op.fields.put("fmList",s.finmon.getOrDefault(c.passport,text(input,"fmList")));
        s.operations.put(op.id,op);
        Optional<Client> duplicate=s.clients.values().stream().filter(x->x.status.equals("Активен") && x.birthDate.equals(c.birthDate) && normalize(x.surname).equals(normalize(c.surname)) && normalize(x.name).equals(normalize(c.name)) && normalize(x.patronymic).equals(normalize(c.patronymic))).findFirst();
        if(duplicate.isPresent()) { op.stage="DUPLICATE"; op.duplicateId=duplicate.get().id; op.message=Messages.DUPLICATE; }
        else afterDuplicate(op);
        return s.operationView(op);
    }
    static String normalize(String value) { return value.trim().toUpperCase(Locale.ROOT).replace('Ё','Е'); }
    Map<String,Object> advance(User user,Map<String,Object> input) {
        Operation op=s.owned(user,text(input,"id")); s.draft(op);
        require(op.type.equals("CREATE_CLIENT") && op.owner.equals(user.login()),403,"Продолжение анкеты недоступно");
        String choice=text(input,"choice");
        if(op.stage.equals("DUPLICATE")) {
            require(List.of("previous","noPrevious").contains(choice),400,"Выберите действие для предыдущего паспорта");
            if(choice.equals("previous")) {
                Client old=s.client(op.duplicateId); String p=passport(text(input,"passport"));
                if(old.passport.equals(p) || old.previousPassports.contains(p)) { op.stage="EXISTING"; op.status="Отменена"; op.message=Messages.PREVIOUS; return s.operationView(op); }
            } else op.needsControl=true;
            afterDuplicate(op);
        } else if(op.stage.equals("FINMON")) {
            require(choice.equals("continue"),400,"Нажмите «Продолжить»");
            op.fields.put("finmonSent",true); finish(op);
        } else throw new Problem(409,"Этот шаг анкеты уже завершён");
        return s.operationView(op);
    }
    void afterDuplicate(Operation op) {
        if(!text(op.fields,"fmList").isEmpty()) { op.stage="FINMON"; op.message=Messages.fm(text(op.fields,"fmList")); }
        else finish(op);
    }
    void finish(Operation op) {
        require(s.clients.values().stream().noneMatch(x->!x.id.equals(op.clientId) && x.passport.equals(op.candidate.passport)),409,"Паспорт уже принадлежит клиенту");
        if(op.needsControl) { op.status="На подтверждении"; op.stage="CONTROL"; op.message=Messages.CLIENT_CONTROL; s.clients.put(op.clientId,op.candidate); }
        else save(op);
    }
    void save(Operation op) {
        require(s.clients.values().stream().noneMatch(x->!x.id.equals(op.clientId) && x.passport.equals(op.candidate.passport)),409,"Паспорт уже принадлежит клиенту");
        op.candidate.status="Активен";
        if(Boolean.TRUE.equals(op.fields.get("finmonSent")) && !op.candidate.history.contains("Передано в финмониторинг")) op.candidate.history.add("Передано в финмониторинг");
        s.clients.put(op.clientId,op.candidate); op.status="Исполнена"; op.stage="SAVED"; op.message=Messages.SAVED;
    }
}
