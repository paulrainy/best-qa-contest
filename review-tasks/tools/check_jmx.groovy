// Проверка сценариев в настоящем JMeter 5.6.3.
//
// Запуск:
//   java -Djava.awt.headless=true -cp "$JMETER_HOME/lib/*:$JMETER_HOME/lib/ext/*" \
//        groovy.ui.GroovyMain check_jmx.groovy <файлы .jmx>
//   ... check_jmx.groovy --sample <GuiClass>...   — XML элемента по умолчанию, образец для jmx.py
//
// Для каждого файла: план загружается SaveService, затем каждый элемент проходит через свой GUI-класс
// (configure → createTestElement). Если GUI вернул другое значение свойства, значит GUI показывает
// не то, что записано в файле: неверное имя или формат свойства. Печатает OK или FAIL, код 1 при FAIL.

import org.apache.jmeter.gui.JMeterGUIComponent
import org.apache.jmeter.save.SaveService
import org.apache.jmeter.testbeans.gui.TestBeanGUI
import org.apache.jmeter.testelement.TestElement
import org.apache.jmeter.testelement.property.BooleanProperty
import org.apache.jmeter.util.JMeterUtils
import org.apache.jorphan.collections.HashTree
import org.apache.jorphan.collections.ListedHashTree

// Свойства, которые GUI выставляет или переписывает сам, — их расхождение ничего не значит.
IGNORED = [
    'TestElement.gui_class',      // GUI пишет полное имя класса, в файле — короткое
    'TestElement.test_class',     // то же
] as Set

def home = System.getenv('JMETER_HOME')
if (!home) {
    System.err.println('Нет JMETER_HOME')
    System.exit(2)
}
JMeterUtils.setJMeterHome(home)
JMeterUtils.loadJMeterProperties("$home/bin/jmeter.properties")
JMeterUtils.initLocale()

def guiFor(TestElement element) {
    def name = SaveService.aliasToClass(element.getPropertyAsString(TestElement.GUI_CLASS))
    if (name == TestBeanGUI.name) {
        // У TestBean-элементов GUI строится по классу самого элемента
        return new TestBeanGUI(element.getClass())
    }
    return (JMeterGUIComponent) Class.forName(name).getDeclaredConstructor().newInstance()
}

def compare(String path, TestElement element, List problems) {
    JMeterGUIComponent gui
    try {
        gui = guiFor(element)
    } catch (Throwable e) {
        problems << "$path: GUI не создаётся: $e"
        return
    }
    try {
        gui.configure(element)
        // В 5.6 createTestElement() даёт элемент со значениями по умолчанию,
        // поля GUI переносит в него modifyTestElement — как при сохранении плана из GUI
        TestElement copy = gui.createTestElement()
        gui.modifyTestElement(copy)
        for (prop in element.propertyIterator()) {
            def name = prop.name
            if (name in IGNORED) continue
            def ours = prop.stringValue
            def shown = copy.getPropertyAsString(name)
            // GUI не пишет булево свойство со значением false: отсутствующее свойство и так читается как false
            if (prop instanceof BooleanProperty) {
                ours = String.valueOf(prop.booleanValue)
                shown = String.valueOf(copy.getPropertyAsBoolean(name))
            }
            if (ours != shown) problems << "$path: $name: наше «$ours», GUI «$shown»"
        }
    } catch (Throwable e) {
        problems << "$path: GUI не открывает элемент: $e"
    }
}

def walk(HashTree tree, String prefix, List problems) {
    for (key in tree.list()) {
        def element = (TestElement) key
        def path = prefix ? "$prefix → ${element.name}" : element.name
        compare(path, element, problems)
        walk(tree.getTree(key), prefix == null ? '' : path, problems)
    }
}

if (args && args[0] == '--sample') {
    for (name in args.drop(1)) {
        // TestBean-элементы (CSV Data Set, JSR223, JDBC…) задаются как TestBeanGUI:<класс элемента>
        def gui = name.startsWith('TestBeanGUI:')
            ? new TestBeanGUI(Class.forName(name.substring('TestBeanGUI:'.length())))
            : (JMeterGUIComponent) Class.forName(name).getDeclaredConstructor().newInstance()
        def tree = new ListedHashTree(gui.createTestElement())
        println "===== $name"
        def buffer = new ByteArrayOutputStream()   // saveTree закрывает поток, System.out закрывать нельзя
        SaveService.saveTree(tree, buffer)
        println buffer.toString('UTF-8')
    }
    System.exit(0)
}

def failed = false
for (file in args) {
    def problems = []
    try {
        walk(SaveService.loadTree(new File(file)), null, problems)
    } catch (Throwable e) {
        problems << "не загружается: $e"
    }
    if (problems) {
        failed = true
        problems.each { println "FAIL $file: $it" }
    } else {
        println "OK $file"
    }
}
System.exit(failed ? 1 : 0)
