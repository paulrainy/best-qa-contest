"""Отдельная временная шкала /metrics и ресурсов генератора, без подстановки нулей."""
import argparse
import csv
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import threading
import time

try:
    from .common import request
except ImportError:
    from common import request

FIELDS = dict(accountingQueue='stand_queue_messages{queue="accounting.transfer-created"}',
              notificationQueue='stand_queue_messages{queue="notifications.transfer-events"}',
              dlqQueue='stand_queue_messages{queue="transfers.dlq"}',
              accountingProcessed='stand_accounting_messages_processed_total',
              finalized='stand_transfer_completion_seconds_count', dbTransfers='stand_db_transfers_rows',
              heapUsed='jvm_memory_heap_used_bytes', heapMax='jvm_memory_heap_max_bytes',
              standCpu='process_cpu_load', standThreads='jvm_threads_live')


def parse_metrics(text):
    raw = {}
    for line in text.splitlines():
        if line and not line.startswith('#'):
            match = re.fullmatch(r'(\S+(?:\{.*\})?)\s+(\S+)', line)
            if match:
                value = float(match.group(2))
                raw[match.group(1)] = value if math.isfinite(value) else None
    values = {field: raw.get(name) for field, name in FIELDS.items()}
    http = [v for k, v in raw.items() if k.startswith('stand_http_requests_total{') and v is not None]
    values['httpRequests'] = sum(http) if http else None
    return values


_WINDOWS_CPU = {}


def _windows_generator_stats(parent_pid):
    """Toolhelp и GetProcessTimes из stdlib: дочерний java.exe лаунчера jmeter.bat либо сам процесс.

    CPU — доля одного логического ядра за время с предыдущего замера этого процесса
    (для первого замера — с его запуска); рабочий набор (Working Set) — аналог RSS.
    """
    import ctypes
    from ctypes import wintypes

    class ProcessEntry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD), ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', ctypes.c_size_t), ('th32ModuleID', wintypes.DWORD),
                    ('cntThreads', wintypes.DWORD), ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', wintypes.WCHAR * 260)]

    class MemoryCounters(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage',
                                                 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                                                 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]

    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    kernel32.GetSystemTimeAsFileTime.argtypes = [ctypes.POINTER(wintypes.FILETIME)]

    def check(ok, what):
        if not ok:
            raise OSError(f'{what}: WinError {ctypes.get_last_error()}')

    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)
    check(snapshot not in (None, wintypes.HANDLE(-1).value), 'CreateToolhelp32Snapshot')
    processes = {}
    children = []
    try:
        entry = ProcessEntry(dwSize=ctypes.sizeof(ProcessEntry))
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            processes[entry.th32ProcessID] = entry.cntThreads
            if entry.th32ParentProcessID == parent_pid and entry.szExeFile.lower() == 'java.exe':
                children.append(entry.th32ProcessID)
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    pid = children[0] if children else parent_pid
    if pid not in processes:
        raise OSError(f'Процесс {pid} не найден')
    handle = kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
    check(handle, 'OpenProcess')
    try:
        creation, exited, kernel, user, now = (wintypes.FILETIME() for _ in range(5))
        check(kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exited),
                                       ctypes.byref(kernel), ctypes.byref(user)), 'GetProcessTimes')
        memory = MemoryCounters(cb=ctypes.sizeof(MemoryCounters))
        check(kernel32.K32GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb), 'GetProcessMemoryInfo')
    finally:
        kernel32.CloseHandle(handle)
    kernel32.GetSystemTimeAsFileTime(ctypes.byref(now))
    ticks = [(t.dwHighDateTime << 32) | t.dwLowDateTime for t in (creation, kernel, user, now)]
    started, cpu, wall = ticks[0], ticks[1] + ticks[2], ticks[3]
    previous_wall, previous_cpu = _WINDOWS_CPU.get((pid, started), (started, 0))
    _WINDOWS_CPU[(pid, started)] = (wall, cpu)
    if wall <= previous_wall or cpu < previous_cpu:
        raise OSError('Нет приращения времени для расчёта CPU')
    return dict(generatorPid=pid, generatorCpuPercent=round(100 * (cpu - previous_cpu) / (wall - previous_wall), 2),
                generatorRssKiB=memory.WorkingSetSize // 1024, generatorThreads=processes[pid])


def generator_stats(parent_pid):
    if not parent_pid:
        return {}
    if platform.system() == 'Windows':
        try:
            return _windows_generator_stats(parent_pid)
        except (OSError, ValueError, AttributeError) as exc:
            return dict(generatorError=str(exc))
    try:
        lines = subprocess.check_output(['ps', '-axo', 'pid=,ppid=,comm='], text=True).splitlines()
        children = [line.split(None, 2) for line in lines]
        pid = next((int(p) for p, parent, command in children if int(parent) == parent_pid and command.endswith('/java')), parent_pid)
        result = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu=,rss='], text=True, stderr=subprocess.PIPE).split()
        if platform.system() == 'Darwin':
            threads = len(subprocess.check_output(['ps', '-M', '-p', str(pid)], text=True, stderr=subprocess.PIPE).splitlines()) - 1
        else:
            threads = int(subprocess.check_output(['ps', '-p', str(pid), '-o', 'nlwp='], text=True, stderr=subprocess.PIPE))
        return dict(generatorPid=pid, generatorCpuPercent=float(result[0]),
                    generatorRssKiB=int(result[1]), generatorThreads=threads)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError) as exc:
        return dict(generatorError=str(exc))


class MetricsCollector:
    def __init__(self, base, output, *, generator_pid=lambda: None, interval=5):
        self.base, self.output = base, Path(output)
        self.generator_pid, self.interval = generator_pid, interval
        self.stop = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self._collect, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def close(self):
        self.stop.set()
        self.thread.join(15)
        if self.thread.is_alive():
            raise RuntimeError('Сборщик метрик не завершился')
        if self.error:
            raise RuntimeError('Не удалось сохранить метрики') from self.error

    def _collect(self):
        try:
            fields = ['timestampMs', 'error', *FIELDS, 'httpRequests', 'generatorPid',
                      'generatorCpuPercent', 'generatorRssKiB', 'generatorThreads', 'generatorError']
            with self.output.open('x', newline='', encoding='utf-8') as csv_file, self.output.with_suffix('.jsonl').open('x', encoding='utf-8') as raw_file:
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                writer.writeheader()
                while True:
                    sample = dict(timestampMs=int(time.time() * 1000), error='')
                    text = ''
                    try:
                        text = request(self.base, '/metrics', timeout=5)
                        sample.update(parse_metrics(text))
                        missing = [k for k in FIELDS if sample.get(k) is None]
                        if missing:
                            sample['error'] = 'Отсутствуют метрики: ' + ','.join(missing)
                    except (OSError, ValueError) as exc:
                        sample['error'] = str(exc)
                    sample.update(generator_stats(self.generator_pid()))
                    writer.writerow(sample)
                    csv_file.flush()
                    raw_file.write(json.dumps(dict(**sample, prometheus=text), ensure_ascii=False) + '\n')
                    raw_file.flush()
                    if self.stop.wait(self.interval):
                        break
        except BaseException as exc:
            self.error = exc


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://localhost:18400')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=60)
    args = parser.parse_args()
    collector = MetricsCollector(args.base_url, args.output).start()
    try:
        time.sleep(args.duration)
    finally:
        collector.close()
