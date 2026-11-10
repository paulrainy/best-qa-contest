@echo off
cd /d "%~dp0"
if defined JAVA_HOME (
  "%JAVA_HOME%\bin\java.exe" -jar transfer-stand.jar
) else (
  java -jar transfer-stand.jar
)
pause
