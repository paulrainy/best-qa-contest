"""Один независимый прогон: reset, CSV, JMeter CLI, метрики, статусы, анализ, PNG."""
import argparse
import hashlib
from importlib.metadata import distributions
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

try:
    from .analyse import analyse
    from .collect_metrics import MetricsCollector, parse_metrics
    from .collect_transfers import collect
    from .common import ROOT, api, properties, read_jtl, request, utf8_output, write_json
    from .prepare_data import prepare
except ImportError:
    from analyse import analyse
    from collect_metrics import MetricsCollector, parse_metrics
    from collect_transfers import collect
    from common import ROOT, api, properties, read_jtl, request, utf8_output, write_json
    from prepare_data import prepare


def capture(command, env=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=20, env=env,
                                stdin=subprocess.DEVNULL, encoding='utf-8', errors='replace')
        return dict(command=command, exit=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        return dict(command=command, error=str(exc))


def powershell(script):
    return capture(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                    '[Console]::OutputEncoding=[Text.Encoding]::UTF8; ' + script])


def stop_tree(process):
    """jmeter.bat — это cmd.exe; без /T его дочерний java.exe переживёт остановку."""
    if os.name == 'nt':
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)], capture_output=True)
    else:
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name != 'nt':
            os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    profile = ROOT / 'profiles' / (args.profile + '.properties')
    settings = properties(profile)
    shutil.copyfile(profile, output / 'profile.properties')
    env = os.environ.copy()
    if args.java_home:
        env['JAVA_HOME'] = str(args.java_home.resolve())
    env.setdefault('HEAP', '-Xms256m -Xmx1g')
    java = str(Path(env['JAVA_HOME']) / 'bin/java') if env.get('JAVA_HOME') else 'java'
    if env.get('JAVA_HOME'):
        # jmeter.bat вызывает java.exe из PATH, а не из JAVA_HOME: записанная JVM должна совпадать с исполняемой.
        env['PATH'] = str(Path(env['JAVA_HOME']) / 'bin') + os.pathsep + env.get('PATH', '')
    url = urlsplit(args.base_url)
    if url.scheme not in ('http', 'https') or not url.hostname or url.path not in ('', '/'):
        raise ValueError('Нужен HTTP(S) base-url без пути')
    jmeter = str(Path(args.jmeter).resolve())
    if not Path(jmeter).is_file():
        raise ValueError('Не найден JMeter executable')
    metadata = dict(startedAtMs=int(time.time() * 1000), python=sys.version, executable=sys.executable,
                    platform=platform.platform(), machine=platform.machine(), cpuCount=os.cpu_count(),
                    java=capture([java, '-version'], env), jmeter=capture([jmeter, '-v'], env),
                    colocated=True, baseUrl=args.base_url, standPid=args.stand_pid,
                    standJarSha256=digest(ROOT / '../../participant/stand/transfer-stand.jar'),
                    hashes={str(p.relative_to(ROOT)): digest(p) for p in sorted(ROOT.glob('tools/*.py'))},
                    jmxSha256=digest(ROOT / 'transfers.jmx'), profileSha256=digest(profile),
                    requirementsSha256=digest(ROOT / 'requirements.txt'),
                    packages={d.metadata['Name']: d.version for d in distributions()},
                    environment={k: env.get(k) for k in ('JAVA_HOME', 'HEAP', 'JVM_ARGS', 'JAVA_TOOL_OPTIONS')})
    if platform.system() == 'Darwin':
        metadata['hardware'] = capture(['sysctl', 'hw.model', 'hw.memsize', 'machdep.cpu.brand_string'])
    elif platform.system() == 'Windows':
        metadata['hardware'] = powershell(
            '$c=Get-CimInstance Win32_Processor; $s=Get-CimInstance Win32_ComputerSystem; $o=Get-CimInstance Win32_OperatingSystem; '
            '"cpu=$($c.Name); logical=$($s.NumberOfLogicalProcessors); ramBytes=$($s.TotalPhysicalMemory); '
            'model=$($s.Manufacturer) $($s.Model); os=$($o.Caption) $($o.Version) $($o.OSArchitecture)"')
        metadata['javaOnPath'] = capture(['where', 'java'], env)
    if args.stand_pid:
        metadata['standCommand'] = (powershell(f'(Get-CimInstance Win32_Process -Filter "ProcessId={args.stand_pid}").CommandLine')
                                    if os.name == 'nt' else capture(['ps', '-p', str(args.stand_pid), '-o', 'command=']))
    write_json(output / 'environment.json', metadata)
    process = None
    collector = None
    try:
        health = api(args.base_url, '/api/v1/health')
        if health.get('status') != 'UP':
            raise RuntimeError(f'Стенд не готов: {health}')
        write_json(output / 'reset.json', api(args.base_url, '/api/test/reset', 'POST'))
        if api(args.base_url, '/api/test/clock')['shifted']:
            raise RuntimeError('После reset часы сдвинуты')
        consumers = api(args.base_url, '/api/test/consumers')
        if consumers != dict(accounting='RUNNING', notifications='RUNNING'):
            raise RuntimeError(f'Потребители не работают: {consumers}')
        from_metrics = request(args.base_url, '/metrics')
        initial = parse_metrics(from_metrics)
        if initial['dbTransfers'] != 30000:
            raise RuntimeError(f'Нестандартная история: {initial["dbTransfers"]}')
        write_json(output / 'initial.json', dict(health=health, consumers=consumers, metrics=initial))
        prepare(args.base_url, output / 'accounts.csv')
        collector = MetricsCollector(args.base_url, output / 'metrics.csv',
                                     generator_pid=lambda: process.pid if process and process.poll() is None else None).start()
        command = [jmeter, '-n', '-t', str(ROOT / 'transfers.jmx'), '-q', str(profile),
                   '-Jaccounts.file=' + str(output / 'accounts.csv'),
                   '-Jhttp.protocol=' + url.scheme, '-Jhttp.host=' + url.hostname,
                   '-Jhttp.port=' + str(url.port or (443 if url.scheme == 'https' else 80)),
                   '-l', str(output / 'samples.jtl'), '-j', str(output / 'jmeter.log'),
                   '-e', '-o', str(output / 'html')]
        metadata['command'] = command
        write_json(output / 'environment.json', metadata)
        with (output / 'jmeter-console.log').open('x', encoding='utf-8') as log:
            # stdin закрыт: при ошибке jmeter.bat выполняет pause и иначе ждал бы клавишу до таймаута.
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=env,
                                       cwd=ROOT, start_new_session=os.name != 'nt')
            metadata['jmeterLauncherPid'] = process.pid
            code = process.wait(timeout=float(settings['load.duration']) + 180)
        metadata['jmeterExit'] = code
        if code != 0:
            raise RuntimeError(f'JMeter завершился с кодом {code}; см. jmeter-console.log')
        rows = read_jtl(output / 'samples.jtl')
        keys = [r['idempotencyKey'] for r in rows if r['label'] == 'POST transfer']
        if not keys:
            raise RuntimeError('JMeter не отправил ни одного POST; см. jmeter.log. '
                               'Groovy 3.0.20 из JMeter 5.6.3 не исполняет JSR223 на Java 25+')
        if len(set(keys)) != len(keys) or len(keys) > 100000:
            raise RuntimeError('Повторный ключ или превышен бюджет данных')
        collect(rows, args.base_url, output / 'transfers.jsonl')
        collector.close()
        collector = None
        summary = analyse(output / 'samples.jtl', output / 'metrics.csv', output / 'transfers.jsonl', profile)
        metadata['postRunClock'] = api(args.base_url, '/api/test/clock')
        metadata['postRunConsumers'] = api(args.base_url, '/api/test/consumers')
        write_json(output / 'summary.json', summary)
        plot = subprocess.run([sys.executable, str(ROOT / 'tools/plot.py'), '--summary', str(output / 'summary.json'),
                               '--metrics', str(output / 'metrics.csv'), '--output', str(output / 'plots')], capture_output=True, text=True)
        (output / 'plot.log').write_text(plot.stdout + plot.stderr, encoding='utf-8')
        metadata['plotExit'] = plot.returncode
        if plot.returncode != 0:
            raise RuntimeError('Не удалось построить графики; см. plot.log')
        print(json.dumps(dict(output=str(output), verdict=summary['nft_verdict'], measured=summary['measured']), ensure_ascii=False), flush=True)
        return 0 if summary['data_complete'] and summary['load_valid'] and summary['metrics']['complete'] and summary['nft_verdict'] != 'UNPROVEN' else 2
    except BaseException as exc:
        metadata['error'] = repr(exc)
        raise
    finally:
        if process and process.poll() is None:
            stop_tree(process)
        if collector:
            collector.close()
        metadata['finishedAtMs'] = int(time.time() * 1000)
        write_json(output / 'environment.json', metadata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['smoke', 'steps', 'confirmation', 'stability'], required=True)
    parser.add_argument('--jmeter', required=True)
    parser.add_argument('--base-url', default='http://localhost:18400')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--java-home', type=Path)
    parser.add_argument('--stand-pid', type=int)
    args = parser.parse_args()
    utf8_output()
    try:
        sys.exit(run(args))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Прогон не выполнен: {exc}', file=sys.stderr)
        sys.exit(1)
