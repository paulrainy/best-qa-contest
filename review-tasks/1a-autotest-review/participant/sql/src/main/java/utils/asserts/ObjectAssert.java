package utils.asserts;

/**
 * Проверки наличия объекта.
 */
public class ObjectAssert<T> extends CftObjectAssert<ObjectAssert<T>, T> {

    public ObjectAssert(T actual, String what) {
        super(actual, what);
    }
}
