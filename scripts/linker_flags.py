"""Select host linker flags for local Elisa-generated test objects."""

from __future__ import annotations

import os
import shlex
import sys


def elisa_test_link_flags() -> list[str]:
    configured = os.environ.get("ELISA_TEST_LINK_FLAGS")
    if configured is not None:
        return shlex.split(configured)
    if sys.platform == "darwin":
        return ["-Wl,-dead_strip"]
    if sys.platform.startswith("linux"):
        return ["-no-pie"]
    return []
