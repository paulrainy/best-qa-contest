#!/usr/bin/env bash
# Собирает обфусцированный стенд и раскладывает его в participant/stand/ (jar + lib/).
# Нужны JDK 17+ с каталогом jmods и Maven. Запуск из любого каталога: bash final-task/jury/build-stand.sh
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="$here/stand-src"
out="$here/../participant/stand"
(cd "$src" && mvn -q -B clean package)
rm -rf "$out/lib" "$out/transfer-stand.jar"
mkdir -p "$out/lib"
cp "$src/target/transfer-stand.jar" "$out/"
cp "$src/target/lib/"*.jar "$out/lib/"
# веб-консоли брокера нужен архив dojo
cp "$src/target/lib/"*.zip "$out/lib/" 2>/dev/null || true
echo "Готово: $out"
