package ru.rshb.playground.manual;

import org.junit.jupiter.api.Test;
import java.net.URI;
import java.net.http.*;
import java.time.LocalDate;
import com.fasterxml.jackson.databind.ObjectMapper;
import static org.junit.jupiter.api.Assertions.*;

class SandboxServerTest {
    final HttpClient client=HttpClient.newHttpClient();
    HttpResponse<String> request(SandboxServer server,String path,String body,String token) throws Exception {
        HttpRequest.Builder builder=HttpRequest.newBuilder(URI.create(server.url()+path));
        if(token!=null) builder.header("Authorization","Bearer "+token);
        if(body==null) builder.GET(); else builder.header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body));
        return client.send(builder.build(),HttpResponse.BodyHandlers.ofString());
    }
    @Test void httpRequiresSessionAndResetRevokesIt() throws Exception {
        try(SandboxServer server=new SandboxServer(0,LocalDate.of(2026,11,5))) {
            server.start();
            assertEquals(401,request(server,"api/action","{\"action\":\"bootstrap\"}",null).statusCode());
            var login=request(server,"api/login","{\"login\":\"tst_oper01\",\"password\":\"Test123!\"}",null);
            assertEquals(200,login.statusCode());
            String token=new ObjectMapper().readTree(login.body()).get("token").asText();
            assertEquals(200,request(server,"api/action","{\"action\":\"bootstrap\"}",token).statusCode());
            assertEquals(200,request(server,"api/reset","{}",token).statusCode());
            assertEquals(401,request(server,"api/action","{\"action\":\"bootstrap\"}",token).statusCode());
        }
    }
    @Test void malformedJsonAndUnknownRoutesReturnClearErrors() throws Exception {
        try(SandboxServer server=new SandboxServer(0,LocalDate.of(2026,11,5))) {
            server.start();
            assertEquals(400,request(server,"api/login","not-json",null).statusCode());
            assertEquals(404,request(server,"missing",null,null).statusCode());
            assertEquals(200,request(server,"",null,null).statusCode());
        }
    }
}
