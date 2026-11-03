#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
JAVA_HOME="$SCRIPT_DIR/tools/java/macos-aarch64/Contents/Home"
JMETER_HOME="$SCRIPT_DIR/tools/apache-jmeter-5.6.3"

if [ ! -x "$JAVA_HOME/bin/java" ] || [ ! -f "$JMETER_HOME/bin/ApacheJMeter.jar" ]; then
    printf '%s\n' 'Не найдены JMeter или Java. Распакуйте комплект целиком.' >&2
    exit 1
fi

cd "$SCRIPT_DIR"
mkdir -p .jmeter

# Параметры доступа к модулям — из штатного запуска JMeter 5.6.3 для Java 17.
exec "$JAVA_HOME/bin/java" -Xms128m -Xmx512m \
    --add-opens=java.desktop/sun.awt=ALL-UNNAMED \
    --add-opens=java.desktop/sun.swing=ALL-UNNAMED \
    --add-opens=java.desktop/javax.swing.text.html=ALL-UNNAMED \
    --add-opens=java.desktop/java.awt=ALL-UNNAMED \
    --add-opens=java.desktop/java.awt.font=ALL-UNNAMED \
    --add-opens=java.base/java.lang=ALL-UNNAMED \
    --add-opens=java.base/java.lang.invoke=ALL-UNNAMED \
    --add-opens=java.base/java.lang.reflect=ALL-UNNAMED \
    --add-opens=java.base/java.util=ALL-UNNAMED \
    --add-opens=java.base/java.text=ALL-UNNAMED \
    --add-opens=java.desktop/sun.awt.shell=ALL-UNNAMED \
    -Duser.language=en -Duser.country=US \
    -Dapple.laf.useScreenMenuBar=true -Xdock:name=JMeter \
    -jar "$JMETER_HOME/bin/ApacheJMeter.jar" -j "$SCRIPT_DIR/.jmeter/jmeter.log" "$@"
