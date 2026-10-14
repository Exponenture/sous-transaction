"""Run against the disposable Compose project created by the Docker CI job."""

import json
import os
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8000"


def request(path, *, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(f"{BASE}{path}", data=data, headers=headers)  # noqa: S310 -- fixed localhost HTTP
    try:
        with urlopen(req, timeout=5) as response:  # noqa: S310
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def main():
    assert os.environ.get("COMPOSE_PROJECT_NAME") == "sous-ci-smoke", (
        "Use the isolated sous-ci-smoke Compose project; never run against a development database."
    )
    for _ in range(30):
        try:
            status, health = request("/api/health/")
            if status == 200 and health == {"status": "ok", "db": "ok"}:
                break
        except (URLError, TimeoutError):
            pass
        time.sleep(1)
    else:
        raise AssertionError("Container API did not become healthy")

    docker = shutil.which("docker")
    assert docker is not None, "Docker CLI is required"
    subprocess.run(  # noqa: S603
        [
            docker,
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "manage.py",
            "shell",
            "-c",
            "from django.contrib.auth import get_user_model; "
            "get_user_model().objects.create_user('ci-smoke', password='ci-smoke-password')",
        ],
        check=True,
    )
    assert request("/api/transactions/")[0] == 401
    status, tokens = request(
        "/api/auth/token/",
        payload={
            "username": "ci-smoke",
            "password": "ci-smoke-password",
        },
    )
    assert status == 200
    token = tokens["access"]
    payload = {
        "transaction_id": "smoke-clean",
        "amount": "-12.50",
        "timestamp": "2024-01-15T12:00:00Z",
        "description": "Unrecognised merchant zxqv",
        "transaction_type": "debit",
        "account_number": "NL91ABNA0417164300",
    }
    status, created = request("/api/transactions/", payload=payload, token=token)
    assert status == 201 and created["status"] == "categorised"
    assert created["categorisation_source"] == "rules"
    assert created["category"] == "Miscellaneous"
    assert request("/api/transactions/", payload=payload, token=token) == (200, created)
    status, detail = request(f"/api/transactions/{created['id']}/", token=token)
    assert status == 200 and detail["raw_payload"] == payload
    status, dirty = request(
        "/api/transactions/",
        payload={
            **payload,
            "transaction_id": "smoke-dirty",
            "amount": "12.50",
        },
        token=token,
    )
    assert status == 201 and dirty["status"] == "quarantined"
    assert request("/api/transactions/", token=token)[1]["count"] == 1
    assert request("/api/transactions/?status=quarantined", token=token)[1]["count"] == 1
    print("Docker smoke passed: health, auth, creation, replay, detail and quarantine")


if __name__ == "__main__":
    main()
