#!/usr/bin/python3
"""Unprivileged local bridge. The systemd unit hides engine and publisher files.
SO_PEERCRED permits only aiinvest. No client command, environment or path is executed.
"""

import concurrent.futures
import json
import os
from pathlib import Path
import pwd
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
from lab_model_events import web_activity

SOCKET = "/run/ai-investment-lab-model/gateway.sock"
BINARY = "/usr/local/libexec/lab-codex-binary"
LIMIT = 1048576


def receive(connection):
    data = bytearray()
    while True:
        chunk = connection.recv(min(65536, LIMIT + 1 - len(data)))
        if not chunk:
            raise ValueError("Incomplete request")
        data.extend(chunk)
        if len(data) > LIMIT:
            raise ValueError("Request too large")
        if data.endswith(b"\n"):
            return json.loads(data)


def execute(request):
    if request == {"version": True}:
        return {
            "version": subprocess.check_output(
                [BINARY, "--version"], text=True, timeout=10
            ).strip()
        }
    if set(request) != {
        "model",
        "reasoning",
        "schema",
        "prompt",
        "web_search",
        "timeout_seconds",
    }:
        raise ValueError("Unsupported request")
    if not isinstance(request["model"], str) or not re.fullmatch(
        r"[A-Za-z0-9_.-]{1,80}", request["model"]
    ):
        raise ValueError("Invalid model")
    if request["reasoning"] not in ("low", "medium", "high", "xhigh"):
        raise ValueError("Invalid reasoning")
    if not isinstance(request["schema"], dict) or not isinstance(
        request["prompt"], str
    ):
        raise ValueError("Invalid input")
    if (
        request["web_search"] not in ("live", "disabled")
        or type(request["timeout_seconds"]) is not int
        or not 1 <= request["timeout_seconds"] <= 600
    ):
        raise ValueError("Unsupported web mode or timeout")
    with tempfile.TemporaryDirectory(prefix="model-") as folder:
        workspace = Path(folder)
        schema = workspace / "schema.json"
        final = workspace / "final.json"
        schema.write_text(json.dumps(request["schema"]))
        args = [
            BINARY,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--json",
            "--color",
            "never",
            "--model",
            request["model"],
            "-c",
            f'model_reasoning_effort="{request["reasoning"]}"',
            "-c",
            'shell_environment_policy.inherit="none"',
            "-c",
            f'web_search="{request["web_search"]}"',
            "--cd",
            folder,
            "--output-schema",
            str(schema),
            "--output-last-message",
            str(final),
            "-",
        ]
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": folder,
            "CODEX_HOME": "/run/lab-codex-auth",
            "TMPDIR": folder,
        }
        with (
            (workspace / "events").open("wb") as events,
            (workspace / "errors").open("wb") as errors,
        ):
            process = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    "/usr/local/libexec/lab-limited-exec.py",
                    "1048576",
                    *args,
                ],
                stdin=subprocess.PIPE,
                stdout=events,
                stderr=errors,
                cwd=folder,
                env=env,
                start_new_session=True,
            )
            try:
                process.communicate(
                    request["prompt"].encode(), timeout=request["timeout_seconds"]
                )
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                return {"error": "TIMEOUT"}
        if process.returncode:
            # Return only categories, never raw logs or authentication details.
            error = (workspace / "errors").read_text(errors="replace")[:4096].lower()
            category = (
                "AUTHENTICATION"
                if any(
                    x in error
                    for x in ("401", "unauthorized", "login", "authentication")
                )
                else "RATE_LIMIT"
                if "429" in error
                else "MODEL_UNAVAILABLE"
                if "model" in error
                and any(
                    x in error for x in ("not supported", "unavailable", "not found")
                )
                else "PROCESS"
            )
            return {"error": category}
        if not final.exists() or final.stat().st_size > 131072:
            return {"error": "MISSING_OR_OVERSIZED_OUTPUT"}
        return {
            "output": json.loads(final.read_bytes()),
            "web_activity": web_activity((workspace / "events").read_bytes()),
        }


def handle(connection):
    with connection:
        connection.settimeout(620)
        uid = struct.unpack(
            "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
        )[1]
        if uid != pwd.getpwnam("aiinvest").pw_uid:
            return
        try:
            response = execute(receive(connection))
        except (ValueError, OSError, KeyError, TypeError):
            response = {"error": "PROCESS"}
        try:
            connection.sendall(json.dumps(response).encode() + b"\n")
        except OSError:
            pass


def main():
    path = Path(SOCKET)
    if path.exists():
        path.unlink()
    with (
        socket.socket(socket.AF_UNIX) as server,
        concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool,
    ):
        server.bind(SOCKET)
        path.chmod(0o660)
        server.listen(4)
        while True:
            connection, _ = server.accept()
            pool.submit(handle, connection)


if __name__ == "__main__":
    main()
