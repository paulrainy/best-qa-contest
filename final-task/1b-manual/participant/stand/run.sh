#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${JAVA_HOME:+$JAVA_HOME/bin/}java" -jar transfer-stand.jar
