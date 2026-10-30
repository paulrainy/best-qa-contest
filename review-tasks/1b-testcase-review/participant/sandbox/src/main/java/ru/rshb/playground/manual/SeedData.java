package ru.rshb.playground.manual;

import static ru.rshb.playground.manual.SandboxStore.*;
import java.time.LocalDate;
import java.util.*;

/** Учебные объекты; названия не содержат номеров кейсов или подсказок к ключу. */
final class SeedData {
    private final SandboxStore s;
    private SeedData(SandboxStore store) { s=store; }
    static void load(SandboxStore store) { new SeedData(store).load(); }
    String client(String passport,String surname,String name,String patronymic,LocalDate born,String fatca,String dbo) {
        return s.prepare(out("entity","client","passport",passport,"surname",surname,"name",name,"patronymic",patronymic,"birthDate",born.toString(),"fatca",fatca,"dbo",dbo,"phone","+7 900 000-00-01")).get("id").toString();
    }
    void account(String c,String number,String balance,String currency,String kind) {
        s.prepare(out("entity","product","clientId",c,"type","account","kind",kind,"number",number,"amount",balance,"currency",currency));
    }
    void deposit(String c,String number,String kind,String amount,int days,int term) {
        s.prepare(out("entity","product","clientId",c,"type","deposit","kind",kind,"number",number,"amount",amount,"opened",s.today.minusDays(days).toString(),"term",Integer.toString(term)));
    }
    void load() {
        LocalDate adult=LocalDate.of(1990,3,12);
        client("4509118230","Иванов","Андрей","Ильич",adult,"NONE","FULL");
        String c=client("4511220345","Петров","Олег","Иванович",adult,"NON_US","FULL");
        account(c,"40817810500000012345","100000","RUB","Текущий");
        account(c,"40817810500000012346","20000","RUB","Карточный");
        client("4512330456","Сидорова","Анна","Петровна",adult,"NON_US","FULL");
        c=client("4513440567","Козлов","Дмитрий","Олегович",adult,"NON_US","FULL");
        account(c,"40817810500000012347","3000000","RUB","Текущий");
        client("4514550678","Морозова","Ольга","Игоревна",adult,"US","FULL");
        client("4515660789","Волков","Игорь","Андреевич",adult,"NON_US","FULL");
        c=client("4516770890","Соколов","Илья","Павлович",adult,"NON_US","FULL");
        account(c,"40817810500000012348","3000000","RUB","Текущий");
        c=client("4517880901","Лебедева","Мария","Олеговна",adult,"NON_US","NONE");
        account(c,"40817810600000023451","1500","RUB","Текущий");
        account(c,"40817810900000023452","0","RUB","Текущий");
        c=client("4523445667","Новиков","Павел","Петрович",adult,"NON_US","FULL");
        deposit(c,"42305810700000078901","Пополняемый","50000",30,181);
        account(c,"40817840200000078902","1000","USD","Текущий");
        c=client("4518990112","Орлова","Ирина","Ивановна",adult,"NON_US","FULL");
        deposit(c,"42305810100000034561","Надёжный","100000",30,181);
        account(c,"40817810300000034562","5000","RUB","Текущий");
        account(c,"40817810300000034563","0","RUB","Карточный");
        account(c,"40817840300000034564","1000","USD","Текущий");
        c=client("4519001223","Зайцев","Никита","Олегович",s.today.minusYears(16),"NON_US","FULL");
        deposit(c,"42301810500000045671","До востребования","15000",30,0);
        account(c,"40817810700000045672","0","RUB","Текущий");
        client("4501334455","Зайцев","Олег","Иванович",LocalDate.of(1980,1,1),"NON_US","FULL");
        c=client("4520112334","Фёдоров","Максим","Олегович",s.today.minusYears(18),"NON_US","FULL");
        deposit(c,"42301810800000056781","До востребования","10000",30,0);
        account(c,"40817810100000056782","0","RUB","Текущий");
        c=client("4521223445","Михайлова","Татьяна","Ивановна",adult,"NON_US","LIMITED");
        deposit(c,"42305810400000067891","Пополняемый","50000",73,181);
        account(c,"40817810400000067892","0","RUB","Текущий");
        c=client("4522334556","Павлов","Сергей","Ильич",adult,"NON_US","FULL");
        account(c,"40817810500000089012","0","RUB","Текущий");
        account(c,"40817810500000089013","0","RUB","Карточный");
        client("4512300111","Семёнова","Алёна","",LocalDate.of(1990,3,12),"NON_US","FULL");
        c=client("4515404001","Карпов","Олег","Дмитриевич",LocalDate.of(1985,7,5),"NON_US","FULL");
        s.clients.get(c).previousPassports.add("4505404000");
        client("4510555777","Лосева","Инна","Павловна",LocalDate.of(1988,9,30),"NON_US","FULL");
        s.finmon.put("4518700701","Решения межведомственной комиссии");
        s.finmon.put("4524600602","Решения межведомственной комиссии");
    }
}
