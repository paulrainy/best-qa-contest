#!/usr/bin/env bash
# Одна сборка на JDK 17; четыре физические runtime-копии.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
java_bin="${JAVA_HOME:+$JAVA_HOME/bin/}java"
version="$("$java_bin" -version 2>&1 | head -1)"
case "$version" in *'"17.'*) ;; *) echo "Для сборки нужен JDK 17: $version" >&2; exit 1;; esac
(cd "$here/stand-src" && mvn -q -B clean package)
for direction in 1a-java 1b-manual 1c-load 1d-python; do
    out="$here/../$direction/participant/stand"
    mkdir -p "$out/lib"
    # Убираются только старые runtime-файлы; пользовательские данные не затрагиваются.
    find "$out/lib" -maxdepth 1 -type f \( -name '*.jar' -o -name '*.zip' \) -delete
    cp "$here/stand-src/target/transfer-stand.jar" "$out/"
    cp "$here/stand-src/target/lib/"*.jar "$out/lib/"
    cp "$here/stand-src/target/lib/"*dojo*.zip "$out/lib/"
    cp "$here/source/"run.sh "$here/source/"run.cmd "$here/source/"stand.properties "$out/"
    cp "$here/source/spec.md" "$out/../spec.md"
done
"${PYTHON:-python3}" "$here/verify/write_manifest.py" --java-version "$version"
"${PYTHON:-python3}" "$here/verify/check_distribution.py" --check
