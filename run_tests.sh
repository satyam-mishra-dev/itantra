#!/usr/bin/env bash
# Every test suite in the repo, one command. Exit non-zero if anything fails.
#   ./run_tests.sh          python + firmware parity (≈1 min)
#   ./run_tests.sh --app    also ./gradlew testDebugUnitTest (needs JDK 17+, Android SDK)
set -euo pipefail
cd "$(dirname "$0")"
PY=p0/.venv/bin/python; [ -x "$PY" ] || PY=python3
echo "== p0"
for t in test_p0 test_wow test_linksim test_reliable test_speak test_phrasebook test_relay test_fec; do
  (cd p0 && "$(pwd)/.venv/bin/python" "$t.py" 2>/dev/null || "$PY" "$t.py") | tail -1
done
echo "== firmware parity"
(cd firmware/lora-bridge && python3 test_frame_compat.py | tail -1)
if [ "${1:-}" = "--app" ]; then
  echo "== app"
  export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"
  (cd app && ./gradlew -q testDebugUnitTest && python3 - <<'PY'
import glob, re
t = f = 0
for x in glob.glob('build/test-results/testDebugUnitTest/*.xml'):
    m = re.search(r'tests="(\d+)" skipped="\d+" failures="(\d+)" errors="(\d+)"', open(x).read())
    t += int(m.group(1)); f += int(m.group(2)) + int(m.group(3))
print(f'app: {t} JUnit tests, {f} failures'); raise SystemExit(1 if f else 0)
PY
  )
fi
echo "ALL GREEN"
