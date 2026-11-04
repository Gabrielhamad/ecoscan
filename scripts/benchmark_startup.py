"""Measure local Streamlit rendering with external services disabled.

This does not measure real authentication, browser latency or hosting cold starts.
"""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ecoscan.services.accounts import UserProfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reruns", type=int, default=5)
    args = parser.parse_args()
    if args.output.exists() or not 1 <= args.reruns <= 20:
        parser.error("Choose a new output file and 1 to 20 reruns")
    results = []
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ, {
            "ECOSCAN_COMMUNITY_ENABLED": "false", "ECOSCAN_OPERATIONS_ENABLED": "false"}))
        stack.enter_context(patch("ecoscan.services.contribution_store.settings", return_value=("", "")))
        for mode in ("guest", "citizen", "admin"):
            app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=30)
            with ExitStack() as identity:
                if mode != "guest":
                    profile = UserProfile("supabase_demo", "Test", "admin" if mode == "admin" else "user")
                    identity.enter_context(patch("ecoscan.ui.streamlit_app.render_identity", return_value=profile))
                for run in range(args.reruns + 1):
                    started = perf_counter()
                    app.run()
                    results.append({"mode": mode, "phase": "first" if run == 0 else "rerun",
                                    "run": run, "seconds": perf_counter() - started,
                                    "errors": [error.message for error in app.exception]})
    payload = {"scope": "local rendering; services disabled; logged-in profiles simulated", "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    if any(result["errors"] for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
