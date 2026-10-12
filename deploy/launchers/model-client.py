#!/usr/bin/python3
"""Codex-compatible client. It has no elevated privileges and never opens auth files."""

import json
from pathlib import Path
import socket
import sys


def request(payload):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(620)
        connection.connect("/run/ai-investment-lab-model/gateway.sock")
        connection.sendall(json.dumps(payload).encode() + b"\n")
        response = bytearray()
        while not response.endswith(b"\n"):
            chunk = connection.recv(65536)
            if not chunk or len(response) + len(chunk) > 1048576:
                raise RuntimeError("Invalid gateway response")
            response.extend(chunk)
        return json.loads(response)


def main():
    args = sys.argv[1:]
    if args == ["--version"]:
        print(request({"version": True})["version"])
        return
    model = args[args.index("--model") + 1]
    schema = args[args.index("--output-schema") + 1]
    output = args[args.index("--output-last-message") + 1]
    reasoning = next(
        x.split("=", 1)[1].strip('"')
        for x in args
        if x.startswith("model_reasoning_effort=")
    )
    response = request(
        {
            "model": model,
            "web_search": next(
                x.split("=", 1)[1].strip('"')
                for x in args
                if x.startswith("web_search=")
            ),
            "timeout_seconds": int(
                next(
                    x.split("=", 1)[1]
                    for x in args
                    if x.startswith("lab_timeout_seconds=")
                )
            ),
            "reasoning": reasoning,
            "schema": json.loads(Path(schema).read_bytes()),
            "prompt": sys.stdin.read(1048576),
        }
    )
    if response.get("error"):
        print(response["error"], file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps({"type": "lab.web_activity", "data": response["web_activity"]}))
    Path(output).write_text(json.dumps(response["output"]))


if __name__ == "__main__":
    main()
