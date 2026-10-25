package main.java.ru.rshb.testitwork.annotations;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Связь автотеста с Test IT. В песочнице только метка: результаты в Test IT не отправляются.
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface TestitStatus {

    String autoTestId();

    String autoTestExternalId();
}
