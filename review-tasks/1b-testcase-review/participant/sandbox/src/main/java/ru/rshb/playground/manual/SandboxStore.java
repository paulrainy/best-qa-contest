package ru.rshb.playground.manual;

import static ru.rshb.playground.manual.Model.*;
import java.math.*;
import java.time.*;
import java.time.temporal.ChronoUnit;
import java.util.*;

/** Изменения выполняются атомарно; наружу возвращаются отдельные снимки. */
public class SandboxStore {
    public final LocalDate today;
    final Map<String,Client> clients = new LinkedHashMap<>();
    final Map<String,Product> products = new LinkedHashMap<>();
    final Map<String,Operation> operations = new LinkedHashMap<>();
    final List<Map<String,Object>> sms = new ArrayList<>();
    final Map<String,String> finmon = new LinkedHashMap<>();
    final Map<String,User> users = new LinkedHashMap<>();
    long sequence;
    public SandboxStore(LocalDate today) {
        this.today = Objects.requireNonNull(today);
        users.put("tst_oper01",new User("tst_oper01","Ирина Соловьёва",Role.OPER,"001"));
        users.put("tst_fk01",new User("tst_fk01","Ксения Литвинова",Role.FK,"001"));
        users.put("tst_kmtp01",new User("tst_kmtp01","Дарья Мельникова",Role.MANAGER,"001"));
        users.put("tst_contr01",new User("tst_contr01","Максим Гаврилин",Role.CONTROLLER,"001"));
        users.put("tst_contr02",new User("tst_contr02","Олег Петров",Role.CONTROLLER,"002"));
        reset();
    }
    public User authenticate(String login, String password) {
        User user = users.get(login);
        require(user != null && "Test123!".equals(password),401,"Неверный логин или пароль");
        return user;
    }
    public synchronized void reset() { clients.clear(); products.clear(); operations.clear(); sms.clear(); finmon.clear(); sequence=0; SeedData.load(this); }
    String next(String prefix) { return prefix.equals("op")?"op-"+UUID.randomUUID():prefix+(++sequence); }
    static String text(Map<String,Object> m,String key) { return Objects.toString(m.get(key),"").trim(); }
    static String value(Map<String,Object> m,String key,String fallback) { String v=text(m,key); return v.isEmpty()?fallback:v; }
    static void require(boolean condition,int status,String message) { if(!condition) throw new Problem(status,message); }
    static Map<String,Object> out(Object... values) {
        Map<String,Object> map = new LinkedHashMap<>();
        for(int i=0;i<values.length;i+=2) map.put(values[i].toString(),values[i+1]);
        return map;
    }
    static LocalDate date(String value) {
        try { return LocalDate.parse(value); } catch(RuntimeException e) { throw new Problem(400,"Некорректная дата: " + value); }
    }
    static BigDecimal amount(String value) {
        String normalized=value.replace(" ","").replace("\u00a0","").replace(',','.');
        require(normalized.matches("\\d{1,15}(\\.\\d{1,2})?"),400,"Укажите неотрицательную сумму с точностью до копеек");
        return new BigDecimal(normalized).setScale(2);
    }
    static String passport(String value) {
        String p=value.replaceAll("\\s","");
        require(p.matches("\\d{10}"),400,"Паспорт: серия 4 цифры и номер 6 цифр");
        return p;
    }
    Client client(String id) { Client c=clients.get(id); require(c!=null,404,"Клиент не найден"); return c; }
    Product product(String id) { Product p=products.get(id); require(p!=null,404,"Продукт не найден"); return p; }
    Operation owned(User user,String id) {
        Operation op=operations.get(id); require(op!=null,404,"Заявка не найдена");
        require(op.owner.equals(user.login()) || (user.role()==Role.CONTROLLER && user.branch().equals(op.branch)),403,"Заявка недоступна пользователю");
        return op;
    }
    void draft(Operation op) { require(op.status.equals("Черновик"),409,"Заявка уже подписана или отменена"); }
    Operation operation(User user,String type,Client c) {
        Operation op=new Operation(); op.id=next("op"); op.type=type; op.owner=user.login(); op.branch=user.branch(); op.clientId=c.id;
        return op;
    }
    public synchronized Map<String,Object> dispatch(User user,String action,Map<String,Object> input) {
        require(user!=null && user.equals(users.get(user.login())),401,"Войдите в песочницу");
        return switch(action) {
            case "bootstrap" -> out("today",today.toString(),"user",userView(user),"clients",clients.values().stream().filter(c->c.status.equals("Активен")).map(this::clientView).toList());
            case "prepare" -> prepare(input);
            case "search" -> {
                String p=passport(text(input,"passport"));
                Client c=clients.values().stream().filter(x->x.status.equals("Активен") && x.passport.equals(p)).findFirst().orElseThrow(()->new Problem(404,"Клиент не найден"));
                yield clientView(c);
            }
            case "client" -> { Client c=client(text(input,"id")); require(c.status.equals("Активен"),404,"Клиент не найден"); yield clientView(c); }
            case "set-fatca" -> {
                require(user.role()==Role.OPER || user.role()==Role.FK,403,"Нет права на изменение FATCA");
                Client c=client(text(input,"clientId")); String f=text(input,"fatca");
                require(List.of("NON_US","US").contains(f),400,"Выберите FATCA-статус"); c.fatca=f; yield clientView(c);
            }
            case "open-deposit" -> openDeposit(user,input);
            case "begin-close" -> beginClose(user,input);
            case "create-client" -> new ClientRegistration(this).create(user,input);
            case "continue-client" -> new ClientRegistration(this).advance(user,input);
            case "cancel" -> {
                Operation op=owned(user,text(input,"id")); draft(op); require(op.owner.equals(user.login()),403,"Отмена доступна инициатору");
                op.status="Отменена"; op.message=""; yield operationView(op);
            }
            case "operation" -> operationView(owned(user,text(input,"id")));
            case "update-operation" -> updateOperation(user,input);
            case "print" -> {
                Operation op=owned(user,text(input,"id")); draft(op);
                require(op.owner.equals(user.login()),403,"Печать доступна инициатору");
                readyToSign(op);
                require(op.signing.equals("Бумажное") && !text(op.fields,"bankOfficer").isEmpty(),400,"Укажите уполномоченное лицо банка");
                op.printed=true; yield operationView(op);
            }
            case "sign" -> sign(user,input);
            case "send-sms" -> {
                Operation op=owned(user,text(input,"id")); draft(op); require(op.owner.equals(user.login()) && op.signing.equals("Электронное"),403,"Электронное подписание недоступно");
                readyToSign(op);
                op.smsCode=Integer.toString(100000+new java.security.SecureRandom().nextInt(900000));
                sms.add(out("operationId",op.id,"clientName",client(op.clientId).fullName(),"phone",value(client(op.clientId).fields,"phone","Учебный телефон"),"code",op.smsCode,"text","Код подтверждения: "+op.smsCode));
                op.message="Клиенту отправлено СМС с кодом"; yield operationView(op);
            }
            case "tasks" -> { require(user.role()==Role.CONTROLLER,403,"Раздел доступен контролёру"); yield out("tasks",operations.values().stream().filter(op->op.status.equals("На подтверждении") && op.branch.equals(user.branch())).map(this::operationView).toList()); }
            case "take" -> {
                Operation op=owned(user,text(input,"id")); require(user.role()==Role.CONTROLLER && op.status.equals("На подтверждении"),403,"Заявка недоступна для исполнения");
                require(op.takenBy.isEmpty() || op.takenBy.equals(user.login()),409,"Заявка взята другим контролёром"); op.takenBy=user.login(); yield operationView(op);
            }
            case "decide" -> decide(user,input);
            case "sms" -> out("messages",List.copyOf(sms));
            default -> throw new Problem(404,"Неизвестное действие: " + action);
        };
    }
    Map<String,Object> prepare(Map<String,Object> input) {
        if(text(input,"entity").equals("finmon")) {
            String p=passport(text(input,"passport")), list=text(input,"list");
            require(list.isEmpty() || List.of("Решения межведомственной комиссии","Перечень организаций и физических лиц, причастных к экстремизму или терроризму").contains(list),400,"Выберите список из BIQ");
            if(list.isEmpty()) finmon.remove(p); else finmon.put(p,list);
            return out("passport",p,"list",list);
        }
        if(text(input,"entity").equals("client")) {
            String p=passport(text(input,"passport")); LocalDate birth=date(text(input,"birthDate"));
            require(!birth.isAfter(today),400,"Дата рождения позже даты операции");
            Client c=clients.get(text(input,"id"));
            require(clients.values().stream().noneMatch(x->!x.id.equals(text(input,"id")) && x.passport.equals(p)),409,"Паспорт уже принадлежит клиенту");
            String fatca=value(input,"fatca","NON_US"), dbo=value(input,"dbo","FULL");
            require(List.of("NON_US","US","NONE").contains(fatca) && List.of("FULL","LIMITED","NONE").contains(dbo),400,"Некорректный FATCA или доступ ДБО");
            require(!text(input,"surname").isEmpty() && !text(input,"name").isEmpty(),400,"Укажите фамилию и имя");
            List<String> previous=new ArrayList<>();
            if(input.containsKey("previousPassports")) for(String v:text(input,"previousPassports").split(",")) if(!v.isBlank()) previous.add(passport(v));
            if(c==null) { c=new Client(); c.id=next("c"); }
            c.surname=text(input,"surname"); c.name=text(input,"name"); c.patronymic=text(input,"patronymic"); c.passport=p; c.birthDate=birth; c.fatca=fatca; c.dbo=dbo;
            c.fields.putAll(input);
            if(input.containsKey("previousPassports")) c.previousPassports=previous;
            clients.put(c.id,c); return clientView(c);
        }
        Client c=client(text(input,"clientId")); String type=value(input,"type","account"), kind=value(input,"kind","Текущий");
        require(List.of("account","deposit").contains(type),400,"Неизвестный тип продукта");
        BigDecimal money=amount(text(input,"amount")); LocalDate opened=date(value(input,"opened",today.minusDays(30).toString()));
        int term;
        try { term=Integer.parseInt(value(input,"term","181")); } catch(NumberFormatException e) { throw new Problem(400,"Некорректный срок"); }
        require(!opened.isAfter(today) && (type.equals("account") || List.of("Надёжный","Пополняемый","До востребования").contains(kind)),400,"Некорректные параметры продукта");
        String id=text(input,"id"); Product p=products.get(id);
        require(p==null || p.clientId.equals(c.id),400,"Продукт принадлежит другому клиенту");
        String number=value(input,"number",String.format(Locale.ROOT,"%020d",sequence+100000));
        require(number.matches("\\d{20}") && products.values().stream().noneMatch(x->!x.id.equals(id) && x.number.equals(number)),400,"Номер продукта должен содержать 20 цифр и быть уникальным");
        String status=value(input,"status","Открыт"),currency=value(input,"currency","RUB");
        require(List.of("Открыт","Закрыт").contains(status) && List.of("RUB","USD","EUR").contains(currency),400,"Некорректный статус или валюта");
        if(p==null) { p=new Product(); p.id=next("p"); }
        p.clientId=c.id; p.type=type; p.kind=kind; p.number=number; p.currency=currency; p.status=status; p.amount=money; p.opened=opened; p.term=kind.equals("До востребования")?0:term;
        products.put(p.id,p); return productView(p);
    }
    static String rate(String kind,String funding) {
        int index=List.of("Со счёта или карты в Банке","Наличными через кассу","Из другого банка").indexOf(funding);
        require(index>=0,400,"Выберите способ внесения средств");
        return switch(kind) { case "Надёжный" -> List.of("16,0","15,5","16,5").get(index); case "Пополняемый" -> List.of("14,0","13,5","14,5").get(index); default -> "0,01"; };
    }
    Map<String,Object> openDeposit(User user,Map<String,Object> in) {
        require(user.role()==Role.OPER || user.role()==Role.FK,403,"У роли нет права на открытие вклада");
        Client c=client(text(in,"clientId")); require(!c.birthDate.plusYears(18).isAfter(today),400,"Открытие вклада доступно клиенту от 18 лет");
        require(!c.fatca.equals("NONE"),400,Messages.FATCA);
        String kind=text(in,"kind"),funding=text(in,"funding");
        require(List.of("Надёжный","Пополняемый","До востребования").contains(kind),400,"Выберите вид вклада");
        BigDecimal sum=amount(text(in,"amount")); BigDecimal min=new BigDecimal(kind.equals("Надёжный")?"10000":kind.equals("Пополняемый")?"1000":"10");
        require(sum.compareTo(min)>=0,400,"Минимальная сумма для вклада «"+kind+"» — "+Messages.money(min)+" ₽");
        require(kind.equals("До востребования") || List.of("181","367").contains(text(in,"term")),400,"Выберите срок 181 или 367 дней");
        String r=rate(kind,funding);
        if(funding.equals("Со счёта или карты в Банке")) eligibleSource(c,text(in,"sourceId"),false);
        String payment=value(in,"interestPayment","Капитализация"); require(List.of("Капитализация","На счёт").contains(payment),400,"Выберите выплату процентов");
        Operation op=operation(user,"OPEN_DEPOSIT",c); op.fields.putAll(out("kind",kind,"amount",sum.toPlainString(),"term",kind.equals("До востребования")?"0":text(in,"term"),"funding",funding,"sourceId",text(in,"sourceId"),"rate",r,"interestPayment",payment));
        op.needsControl=sum.compareTo(new BigDecimal("1000000"))>0 || c.fatca.equals("US");
        op.message=c.fatca.equals("US")?Messages.US:"";
        operations.put(op.id,op); return operationView(op);
    }
    Product eligibleSource(Client c,String id,boolean currentOnly) {
        Product p=product(id); require(p.clientId.equals(c.id) && p.type.equals("account") && p.status.equals("Открыт") && p.currency.equals("RUB") && (!currentOnly || p.kind.equals("Текущий")),400,"Выберите открытый рублёвый счёт клиента"); return p;
    }
    Map<String,Object> updateOperation(User user,Map<String,Object> input) {
        Operation op=owned(user,text(input,"id")); draft(op); require(op.owner.equals(user.login()),403,"Изменение доступно инициатору");
        require(!op.type.equals("CREATE_CLIENT"),400,"Для анкеты используйте её форму");
        if(op.type.startsWith("CLOSE")) {
            Client c=client(op.clientId); boolean minor=c.birthDate.plusYears(18).isAfter(today);
            if(input.containsKey("targetId")) eligibleSource(c,text(input,"targetId"),true);
            if(input.containsKey("representativeId")) { Client r=client(text(input,"representativeId")); require(!r.birthDate.plusYears(18).isAfter(today) && r.status.equals("Активен"),400,"Выберите совершеннолетнего законного представителя"); }
            if(input.containsKey("signing")) require(List.of("Бумажное","Электронное").contains(text(input,"signing")) && (!text(input,"signing").equals("Электронное") || (!minor && c.dbo.equals("FULL"))),400,"Электронное подписание недоступно");
            for(String key:List.of("targetId","representativeId","signing")) if(input.containsKey(key)) {
                op.fields.put(key,text(input,key)); op.printed=false;
                if(key.equals("signing") && !op.signing.equals(text(input,key))) { op.signing=text(input,key); op.smsCode=""; }
            }
            if(Boolean.TRUE.equals(input.get("continuePaper"))) { op.stage="PARAMETERS"; op.message=""; }
        }
        if(input.containsKey("bankOfficer")) { op.fields.put("bankOfficer",text(input,"bankOfficer")); op.printed=false; }
        return operationView(op);
    }
    Map<String,Object> beginClose(User user,Map<String,Object> input) {
        Product p=product(text(input,"productId")); Client c=client(p.clientId);
        require(user.role()==Role.OPER || (user.role()==Role.FK && p.type.equals("deposit")),403,"У роли нет права на закрытие продукта");
        require(p.status.equals("Открыт"),400,"Закрыть можно только открытый продукт");
        boolean deposit=p.type.equals("deposit");
        require(deposit || p.kind.equals("Текущий"),400,"Карточный счёт закрыть нельзя");
        if(!deposit) require(p.amount.signum()==0,400,"Для закрытия счёта остаток должен быть равен 0,00 ₽. Текущий остаток: "+Messages.money(p.amount)+" ₽");
        else require(products.values().stream().anyMatch(a->a.clientId.equals(c.id) && a.type.equals("account") && a.kind.equals("Текущий") && a.currency.equals("RUB") && a.status.equals("Открыт")),400,Messages.NO_ACCOUNT);
        boolean minor=c.birthDate.plusYears(18).isAfter(today);
        boolean early=deposit && p.term>0 && today.isBefore(p.opened.plusDays(p.term));
        require(!deposit || p.term==0 || early,400,"BIQ не определяет выплату срочного вклада в день окончания срока и позже. Этот расчёт не поддерживается песочницей.");
        BigDecimal payout=p.amount;
        if(early) payout=p.amount.add(p.amount.multiply(new BigDecimal("0.0001")).multiply(BigDecimal.valueOf(ChronoUnit.DAYS.between(p.opened,today))).divide(new BigDecimal("365"),12,RoundingMode.HALF_UP)).setScale(2,RoundingMode.HALF_UP);
        Operation op=operation(user,deposit?"CLOSE_DEPOSIT":"CLOSE_ACCOUNT",c); op.productId=p.id;
        op.signing=!minor && c.dbo.equals("FULL")?"Электронное":"Бумажное";
        op.fields.putAll(out("minor",minor,"early",early,"payout",payout.toPlainString(),"originalAmount",p.amount.toPlainString(),"number",p.number,"kind",p.kind,"earlyMessage",early?Messages.EARLY:""));
        if(minor) op.message=Messages.MINOR;
        else if(!c.dbo.equals("FULL")) { op.stage="DBO"; op.message=Messages.DBO; }
        operations.put(op.id,op); return operationView(op);
    }
    void readyToSign(Operation op) {
        require(!op.type.equals("CREATE_CLIENT"),400,"Анкета не требует подписания");
        if(op.type.startsWith("CLOSE")) {
            require(op.stage.equals("PARAMETERS"),400,"Продолжите с бумажным подписанием или отмените операцию");
            Product p=product(op.productId); require(p.status.equals("Открыт") && p.amount.compareTo(amount(text(op.fields,"originalAmount")))==0,409,"Условия продукта изменились; начните операцию заново");
            if(Boolean.TRUE.equals(op.fields.get("minor"))) {
                Client r=client(text(op.fields,"representativeId")); require(r.status.equals("Активен") && !r.birthDate.plusYears(18).isAfter(today),400,"Выберите законного представителя");
            }
            if(op.type.equals("CLOSE_DEPOSIT")) eligibleSource(client(op.clientId),text(op.fields,"targetId"),true);
        }
    }
    Map<String,Object> sign(User user,Map<String,Object> input) {
        Operation op=owned(user,text(input,"id")); draft(op); require(op.owner.equals(user.login()),403,"Подписание доступно инициатору");
        readyToSign(op);
        if(op.signing.equals("Электронное")) {
            require(!op.smsCode.isEmpty(),400,"Сначала нажмите «Отправить код»");
            String code=text(input,"code"); require(code.matches("\\d{6}"),400,"Введите код из 6 цифр");
            if(!op.smsCode.equals(code)) {
                op.attempts--; op.message="Неверный код. Осталось попыток: "+op.attempts;
                if(op.attempts==0) { op.status="Отменена"; op.message=Messages.EXHAUSTED; }
                return operationView(op);
            }
        } else require(op.printed && !text(op.fields,"bankOfficer").isEmpty(),400,"Сначала заполните уполномоченное лицо банка и нажмите «Печать»");
        if(op.type.equals("CLOSE_DEPOSIT")) op.needsControl=op.signing.equals("Бумажное");
        if(op.needsControl) { op.status="На подтверждении"; op.message=Messages.CONTROL; }
        else execute(op);
        return operationView(op);
    }
    Map<String,Object> decide(User user,Map<String,Object> input) {
        Operation op=owned(user,text(input,"id"));
        require(user.role()==Role.CONTROLLER && op.status.equals("На подтверждении") && op.takenBy.equals(user.login()),409,"Сначала возьмите заявку на исполнение");
        boolean approve=Boolean.TRUE.equals(input.get("approve"));
        if(approve) execute(op);
        else { require(!text(input,"comment").isEmpty(),400,"Укажите причину в поле «Комментарий»"); op.status=op.type.equals("CREATE_CLIENT")?"Отменена":"Отклонена"; op.fields.put("comment",text(input,"comment")); op.message=""; if(op.type.equals("CREATE_CLIENT")) clients.remove(op.clientId); }
        return operationView(op);
    }
    void execute(Operation op) {
        if(op.type.equals("CREATE_CLIENT")) { new ClientRegistration(this).save(op); return; }
        Client c=client(op.clientId);
        if(op.type.startsWith("CLOSE")) {
            readyToSign(op);
            Product p=product(op.productId);
            if(op.type.equals("CLOSE_DEPOSIT")) { Product target=eligibleSource(c,text(op.fields,"targetId"),true); target.amount=target.amount.add(amount(text(op.fields,"payout"))); }
            p.status="Закрыт"; op.status="Исполнена"; op.message=""; return;
        }
        Product p=new Product(); p.id=next("p"); p.clientId=c.id; p.type="deposit"; p.kind=text(op.fields,"kind"); p.number=String.format(Locale.ROOT,"423%017d",sequence); p.amount=amount(text(op.fields,"amount")); p.opened=today; p.term=Integer.parseInt(text(op.fields,"term"));
        products.put(p.id,p); op.productId=p.id; op.status="Исполнена"; op.message="";
    }
    Map<String,Object> userView(User u) { return out("login",u.login(),"fullName",u.fullName(),"role",u.role().name(),"branch",u.branch()); }
    Map<String,Object> productView(Product p) { return out("id",p.id,"clientId",p.clientId,"type",p.type,"kind",p.kind,"number",p.number,"currency",p.currency,"status",p.status,"amount",p.amount.toPlainString(),"opened",p.opened.toString(),"term",p.term); }
    Map<String,Object> clientView(Client c) {
        return out("id",c.id,"surname",c.surname,"name",c.name,"patronymic",c.patronymic,"fullName",c.fullName(),"passport",c.passport,"birthDate",c.birthDate.toString(),"status",c.status,"fatca",c.fatca,"dbo",c.dbo,"fields",new LinkedHashMap<>(c.fields),"previousPassports",List.copyOf(c.previousPassports),"history",List.copyOf(c.history),
            "accounts",products.values().stream().filter(p->p.clientId.equals(c.id) && p.type.equals("account")).map(this::productView).toList(),"deposits",products.values().stream().filter(p->p.clientId.equals(c.id) && p.type.equals("deposit")).map(this::productView).toList());
    }
    Map<String,Object> operationView(Operation op) {
        Client c=op.candidate==null?clients.get(op.clientId):op.candidate;
        return out("id",op.id,"type",op.type,"clientId",op.clientId,"clientName",c==null?"":c.fullName(),"productId",op.productId,"status",op.status,"stage",op.stage,"signing",op.signing,"printed",op.printed,"message",op.message,"attempts",op.attempts,"fields",new LinkedHashMap<>(op.fields),"takenBy",op.takenBy,"existingId",op.duplicateId,"duplicate",op.duplicateId.isEmpty()?Map.of():clientView(client(op.duplicateId)));
    }
}
