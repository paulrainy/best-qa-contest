package stand;

import org.apache.qpid.server.SystemLauncher;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/** Встроенный AMQP 0-9-1 брокер (Apache Qpid Broker-J) с веб-консолью. Данные только в памяти. */
final class EmbeddedBroker {

    private EmbeddedBroker() {
    }

    static void start(Main.Config cfg) throws Exception {
        Path work = Files.createTempDirectory("transfer-stand-broker");
        String user = cfg.str("amqp.user");
        String password = cfg.str("amqp.password");
        String json = """
                {
                  "name": "transfer-stand",
                  "modelVersion": "9.0",
                  "authenticationproviders": [{
                    "name": "plain", "type": "Plain", "secureOnlyMechanisms": [],
                    "users": [{"name": "%s", "password": "%s", "type": "managed"}]
                  }],
                  "ports": [
                    {"name": "AMQP", "port": "%d", "bindingAddress": "localhost",
                     "protocols": ["AMQP_0_9_1"], "authenticationProvider": "plain",
                     "virtualhostaliases": [
                       {"name": "nameAlias", "type": "nameAlias"},
                       {"name": "defaultAlias", "type": "defaultAlias"},
                       {"name": "slash", "type": "patternMatchingAlias", "pattern": "/", "virtualHostNode": "default"}
                     ]},
                    {"name": "HTTP", "port": "%d", "bindingAddress": "localhost",
                     "protocols": ["HTTP"], "authenticationProvider": "plain"}
                  ],
                  "virtualhostnodes": [{
                    "name": "default", "type": "Memory", "defaultVirtualHostNode": "true",
                    "virtualHostInitialConfiguration": "{\\"type\\":\\"Memory\\"}"
                  }],
                  "plugins": [{
                    "type": "MANAGEMENT-HTTP", "name": "httpManagement",
                    "httpBasicAuthenticationEnabled": true, "httpSaslAuthenticationEnabled": true
                  }]
                }
                """.formatted(user, password, cfg.integer("amqp.port"), cfg.integer("broker.console.port"));
        Path cfgFile = work.resolve("initial-config.json");
        Files.writeString(cfgFile, json);

        System.setProperty("qpid.work_dir", work.toString());
        Map<String, Object> attrs = new HashMap<>();
        attrs.put("type", "Memory");
        attrs.put("initialConfigurationLocation", cfgFile.toUri().toString());
        attrs.put("startupLoggedToSystemOut", false);
        new SystemLauncher().startup(attrs);
        System.out.println("  брокер запущен");
    }
}
