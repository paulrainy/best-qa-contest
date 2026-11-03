@echo off
setlocal
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
set "JAVA_HOME=%SCRIPT_DIR%tools\java\windows-x64"
set "JMETER_HOME=%SCRIPT_DIR%tools\apache-jmeter-5.6.3"

if not exist "%JAVA_HOME%\bin\java.exe" goto missing
if not exist "%JMETER_HOME%\bin\ApacheJMeter.jar" goto missing

set "PATH=%JAVA_HOME%\bin;%PATH%"
set "JM_LAUNCH=%JAVA_HOME%\bin\java.exe"
set "JMETER_BIN=%JMETER_HOME%\bin\"
set "HEAP=-Xms128m -Xmx512m"
pushd "%SCRIPT_DIR%"
if not exist ".jmeter" mkdir ".jmeter"
call "%JMETER_HOME%\bin\jmeter.bat" -j "%SCRIPT_DIR%.jmeter\jmeter.log" %*
set "JMETER_EXIT=%ERRORLEVEL%"
popd
exit /b %JMETER_EXIT%

:missing
echo Не найдены JMeter или Java. Распакуйте комплект целиком.
pause
exit /b 1
