import time


def wait_for(fetch, accepts, description, timeout_s=10, *,
             monotonic=time.monotonic, sleep=time.sleep):
    deadline = monotonic() + timeout_s
    while True:
        value = fetch()
        if accepts(value):
            return value
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError(f"{description}: timeout {timeout_s}s; последнее значение {value!r}")
        sleep(min(0.05, remaining))


def wait_final(api, transfer_id, timeout_s=10, **clock):
    return wait_for(lambda: api.get(f"/api/v1/transfers/{transfer_id}"),
                    lambda transfer: transfer["status"] in ("COMPLETED", "FAILED"),
                    f"Перевод {transfer_id}", timeout_s, **clock)
