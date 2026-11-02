package ru.rshb.playground.manual;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.*;

/** Локальный HTTP-сервер; весь бизнес-домен находится в SandboxStore. */
public final class SandboxServer implements AutoCloseable {
    private static final ObjectMapper JSON=new ObjectMapper();
    private final HttpServer server;
    private final ExecutorService executor=Executors.newFixedThreadPool(8);
    private final SandboxStore store;
    private final Map<String,Model.User> sessions=new ConcurrentHashMap<>();
    private final Object sessionLock=new Object();
    public SandboxServer(int port,LocalDate today) throws IOException {
        store=new SandboxStore(today);
        server=HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(),port),0);
        server.setExecutor(executor); server.createContext("/efr/",this::handle);
    }
    public void start() { server.start(); }
    public String url() { return "http://localhost:"+server.getAddress().getPort()+"/efr/"; }
    @Override public void close() { server.stop(0); executor.shutdownNow(); }
    public static void main(String[] args) throws Exception {
        int port=Integer.getInteger("efr.port",18081);
        LocalDate today=LocalDate.parse(System.getProperty("efr.today",LocalDate.now().toString()));
        SandboxServer sandbox;
        try { sandbox=new SandboxServer(port,today); }
        catch(BindException e) { throw new IllegalStateException("Порт "+port+" занят. Остановите другое приложение или задайте -Defr.port=18082",e); }
        Runtime.getRuntime().addShutdownHook(new Thread(sandbox::close)); sandbox.start();
        System.out.println("Песочница 1b: "+sandbox.url());
        System.out.println("Дата операции: "+today+". Пароль учебных пользователей: Test123!");
        new java.util.concurrent.CountDownLatch(1).await();
    }
    private void handle(HttpExchange ex) throws IOException {
        try {
            String path=ex.getRequestURI().getPath();
            if(path.startsWith("/efr/api/")) {
                synchronized(sessionLock) { api(ex,path.substring("/efr/api/".length())); }
            } else staticFile(ex,path);
        } catch(Model.Problem e) { send(ex,e.status,Map.of("error",e.getMessage())); }
        catch(com.fasterxml.jackson.core.JacksonException e) { send(ex,400,Map.of("error","Неверный JSON: нужен объект с полями запроса")); }
        catch(Exception e) { e.printStackTrace(System.err); send(ex,500,Map.of("error","Внутренняя ошибка песочницы")); }
        finally { ex.close(); }
    }
    private void api(HttpExchange ex,String path) throws IOException {
        String method=ex.getRequestMethod();
        if(path.equals("session") && method.equals("GET")) { send(ex,200,store.dispatch(current(ex),"bootstrap",Map.of())); return; }
        SandboxStore.require(method.equals("POST"),405,"Используйте POST");
        byte[] bytes=ex.getRequestBody().readNBytes(1_048_577);
        SandboxStore.require(bytes.length<=1_048_576,413,"Слишком большой запрос");
        Map<String,Object> data=JSON.readValue(bytes,new TypeReference<Map<String,Object>>() {});
        SandboxStore.require(data!=null,400,"Нужен JSON-объект");
        if(path.equals("login")) {
            Model.User user=store.authenticate(SandboxStore.text(data,"login"),SandboxStore.text(data,"password"));
            String token=UUID.randomUUID().toString(); sessions.put(token,user);
            Map<String,Object> response=new LinkedHashMap<>(store.userView(user)); response.put("token",token);
            send(ex,200,response); return;
        }
        Model.User user=current(ex);
        if(path.equals("action")) { send(ex,200,store.dispatch(user,SandboxStore.text(data,"action"),data)); return; }
        if(path.equals("reset")) { store.reset(); sessions.clear(); send(ex,200,Map.of("message","Исходные данные восстановлены. Войдите заново.")); return; }
        if(path.equals("logout")) { sessions.remove(token(ex)); send(ex,200,Map.of()); return; }
        throw new Model.Problem(404,"Неизвестный адрес API");
    }
    private String token(HttpExchange ex) { return Optional.ofNullable(ex.getRequestHeaders().getFirst("Authorization")).orElse("").replaceFirst("^Bearer ",""); }
    private Model.User current(HttpExchange ex) { Model.User user=sessions.get(token(ex)); SandboxStore.require(user!=null,401,"Сессия истекла, войдите заново"); return user; }
    private void send(HttpExchange ex,int status,Object data) throws IOException {
        byte[] bytes=JSON.writeValueAsBytes(data); ex.getResponseHeaders().set("Content-Type","application/json; charset=UTF-8");
        ex.getResponseHeaders().set("Cache-Control","no-store"); ex.sendResponseHeaders(status,bytes.length); ex.getResponseBody().write(bytes);
    }
    private void staticFile(HttpExchange ex,String path) throws IOException {
        SandboxStore.require(ex.getRequestMethod().equals("GET"),405,"Используйте GET");
        String file=path.equals("/efr/")?"index.html":path.substring("/efr/".length());
        SandboxStore.require(List.of("index.html","app.js","app.css").contains(file),404,"Страница не найдена");
        try(InputStream input=getClass().getResourceAsStream("/efr/"+file)) {
            SandboxStore.require(input!=null,404,"Страница не найдена"); byte[] bytes=input.readAllBytes();
            String type=file.endsWith(".js")?"text/javascript":file.endsWith(".css")?"text/css":"text/html";
            ex.getResponseHeaders().set("Content-Type",type+"; charset=UTF-8"); ex.getResponseHeaders().set("Cache-Control","no-store");
            ex.sendResponseHeaders(200,bytes.length); ex.getResponseBody().write(bytes);
        }
    }
}
