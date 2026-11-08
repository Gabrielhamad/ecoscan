#!/usr/bin/env bash
set -euo pipefail
# Official Linux x86_64 release; checksum verified before extracting/executing.
target="${1:?pass a writable tools directory}"
mkdir -p "$target"
archive="$target/gitleaks_8.24.3_linux_x64.tar.gz"
curl --fail --silent --show-error --location --retry 2 \
  https://github.com/gitleaks/gitleaks/releases/download/v8.24.3/gitleaks_8.24.3_linux_x64.tar.gz \
  --output "$archive"
python - "$archive" <<'PY'
import hashlib
from pathlib import Path
import sys
expected = '9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c'
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() != expected:
    raise SystemExit('Gitleaks checksum mismatch')
PY
tar -xzf "$archive" -C "$target" gitleaks
