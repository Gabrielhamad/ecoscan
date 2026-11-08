"""Start local Streamlit health endpoint and render a guest page without external services."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def check_startup() -> dict:
    from streamlit.testing.v1 import AppTest
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    env = {**os.environ, 'ECOSCAN_OPERATIONS_ENABLED': 'false', 'ECOSCAN_COMMUNITY_ENABLED': 'false'}
    started = time.monotonic()
    process = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'streamlit_app.py'),
                                '--server.address=127.0.0.1', f'--server.port={port}', '--server.headless=true',
                                '--browser.gatherUsageStats=false'], cwd=ROOT, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        healthy = False
        while time.monotonic() - started < 30:
            if process.poll() is not None:
                raise RuntimeError('Streamlit exited before healthcheck')
            try:
                with urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                    healthy = response.status == 200 and response.read(16) == b'ok'
            except (OSError, URLError):
                pass
            if healthy:
                break
            time.sleep(.1)
        if not healthy:
            raise RuntimeError('Streamlit healthcheck timed out')
        with (patch.dict(os.environ, env),
              patch('ecoscan.services.contribution_store.settings', return_value=('', ''))):
            app = AppTest.from_file(str(ROOT / 'streamlit_app.py'), default_timeout=30).run()
            if app.exception:
                raise RuntimeError('Guest rendering failed; inspect locally without private data')
        return {'server_health': 'passed', 'guest_render': 'passed',
                'elapsed_ms': round((time.monotonic() - started) * 1000, 1),
                'scope': 'local HTTP health and AppTest rendering; no physical camera, login or production database'}
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    result = check_startup()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
