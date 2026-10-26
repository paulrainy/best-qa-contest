# Обфускация классов стенда. Библиотеки (Qpid, RabbitMQ client, H2, Jackson) не трогаем.
-libraryjars <java.home>/jmods/java.base.jmod(!**.jar;!module-info.class)
-libraryjars <java.home>/jmods/java.sql.jmod(!**.jar;!module-info.class)
-libraryjars <java.home>/jmods/java.management.jmod(!**.jar;!module-info.class)
-libraryjars <java.home>/jmods/jdk.management.jmod(!**.jar;!module-info.class)
-libraryjars <java.home>/jmods/jdk.httpserver.jmod(!**.jar;!module-info.class)
-libraryjars <java.home>/jmods/java.logging.jmod(!**.jar;!module-info.class)

-keep public class stand.Main {
    public static void main(java.lang.String[]);
}

-dontoptimize
-repackageclasses ''
-overloadaggressively
-allowaccessmodification
-keepattributes Exceptions,InnerClasses,Signature
-renamesourcefileattribute x
-dontnote **
-dontwarn org.apache.qpid.**,com.rabbitmq.**,org.h2.**,tools.jackson.**,org.slf4j.**
