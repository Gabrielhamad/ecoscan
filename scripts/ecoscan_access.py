from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"


def _lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return str(sock.getsockname()[0])
    except OSError:
        pass

    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not address.startswith("127."):
                return address
    except OSError:
        pass
    return "127.0.0.1"


def _http_ok(url: str, timeout: float = 4.0) -> bool:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "EcoScanAccessCheck/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= int(response.status) < 500
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def _listeners_by_port(ports: tuple[int, ...]) -> dict[int, set[int]]:
    listeners = {port: set() for port in ports}
    if os.name != "nt":
        return listeners

    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return listeners

    pattern = re.compile(r"^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$", re.IGNORECASE)
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        port = int(match.group(1))
        if port in listeners:
            listeners[port].add(int(match.group(2)))
    return listeners


def _stop_listeners(ports: tuple[int, ...]) -> None:
    listeners = _listeners_by_port(ports)
    process_ids = sorted({pid for pids in listeners.values() for pid in pids})
    for process_id in process_ids:
        subprocess.run(
            ["taskkill", "/PID", str(process_id), "/F"],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _start_process(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        env=_env(),
    )


def _wait_for_services(streamlit_port: int, live_port: int, *, timeout: float) -> tuple[bool, bool]:
    deadline = time.monotonic() + timeout
    streamlit_ok = False
    live_ok = False
    while time.monotonic() < deadline:
        streamlit_ok = streamlit_ok or _http_ok(f"http://localhost:{streamlit_port}/")
        live_ok = live_ok or _http_ok(f"http://localhost:{live_port}/health")
        if streamlit_ok and live_ok:
            break
        time.sleep(0.7)
    return streamlit_ok, live_ok


def _print_links(*, lan_ip: str, streamlit_port: int, live_port: int, streamlit_ok: bool, live_ok: bool) -> None:
    print("")
    print("EcoScan - links de acesso")
    print("=" * 34)
    print(f"Status app principal: {'OK' if streamlit_ok else 'NAO RESPONDEU'}")
    print(f"Status camera ao vivo: {'OK' if live_ok else 'NAO RESPONDEU'}")
    print("")
    print("Neste computador:")
    print(f"  Usuario: http://localhost:{streamlit_port}/?profile=usuario_demo")
    print(f"  Admin:   http://localhost:{streamlit_port}/?profile=admin_secretaria")
    print(f"  Live:    http://localhost:{live_port}/")
    print("")
    print("Celular ou outro PC na mesma rede Wi-Fi:")
    print(f"  Usuario: http://{lan_ip}:{streamlit_port}/?profile=usuario_demo")
    print(f"  Admin:   http://{lan_ip}:{streamlit_port}/?profile=admin_secretaria")
    print(f"  Live:    http://{lan_ip}:{live_port}/")
    print("")
    print("Observacao para celular:")
    print("  Upload de imagem funciona via HTTP na rede local.")
    print("  Camera ao vivo pode exigir HTTPS por regra do navegador.")
    print("  Para uso por qualquer pessoa fora da rede, publique o app em HTTPS.")
    print("")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start and diagnose EcoScan access for PC and mobile devices.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--streamlit-port", type=int, default=8501)
    parser.add_argument("--live-port", type=int, default=8765)
    parser.add_argument("--restart", action="store_true", help="Stop listeners on EcoScan ports before starting.")
    parser.add_argument("--check-only", action="store_true", help="Only show the current service status and links.")
    parser.add_argument("--detach", action="store_true", help="Start services and return instead of keeping this console open.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ports = (args.streamlit_port, args.live_port)
    lan_ip = _lan_ip()

    if args.restart:
        _stop_listeners(ports)
        time.sleep(1.5)

    streamlit_ok = _http_ok(f"http://localhost:{args.streamlit_port}/")
    live_ok = _http_ok(f"http://localhost:{args.live_port}/health")

    processes: list[subprocess.Popen] = []
    if not args.check_only:
        if not streamlit_ok:
            processes.append(
                _start_process(
                    [
                        "scripts/run_streamlit_app.py",
                        "--host",
                        args.host,
                        "--port",
                        str(args.streamlit_port),
                    ]
                )
            )
        if not live_ok:
            processes.append(
                _start_process(
                    [
                        "scripts/run_live_camera_app.py",
                        "--host",
                        args.host,
                        "--port",
                        str(args.live_port),
                    ]
                )
            )
        streamlit_ok, live_ok = _wait_for_services(
            args.streamlit_port,
            args.live_port,
            timeout=25.0,
        )

    _print_links(
        lan_ip=lan_ip,
        streamlit_port=args.streamlit_port,
        live_port=args.live_port,
        streamlit_ok=streamlit_ok,
        live_ok=live_ok,
    )

    if args.check_only or args.detach or not processes:
        return 0 if streamlit_ok else 1

    print("Servidores iniciados por este terminal. Pressione Ctrl+C para encerrar.")
    try:
        while True:
            for process in processes:
                if process.poll() is not None:
                    return int(process.returncode or 0)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nEncerrando EcoScan...")
        for process in processes:
            process.terminate()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
