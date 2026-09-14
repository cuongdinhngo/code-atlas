"""Fake git for the native-Windows wedge proving test (task 271).

Spawns a grandchild that INHERITS and HOLDS the capture pipe's write end, then keeps the whole
tree alive. The reader (``_run``) sees EOF only once every holder dies, so on Windows only a
process-TREE kill frees it — a plain ``kill()`` of the direct child leaves the grandchild holding
the pipe, which is exactly the wedge the fix backstops.
"""

import subprocess
import sys
import time
from pathlib import Path

HOLD_SECONDS = 60


def main() -> None:
    sentinel = Path(sys.argv[1])
    grandchild = subprocess.Popen(
        [sys.executable, "-c", f"import time; time.sleep({HOLD_SECONDS})"],
        stdout=sys.stdout,
        close_fds=False,
    )
    sentinel.write_text("grandchild-holds-the-pipe", encoding="utf-8")
    try:
        time.sleep(HOLD_SECONDS)
    finally:
        grandchild.kill()


if __name__ == "__main__":
    main()
