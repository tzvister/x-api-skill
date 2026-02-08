"""Shared fixtures for xpost integration tests."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ── Paths ──

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPT = ROOT_DIR / "scripts" / "xpost.py"
ENV_FILE = ROOT_DIR / ".env"


# ── Environment Setup ──

def pytest_configure(config):
    """Load .env before any tests run."""
    load_dotenv(ENV_FILE, override=True)


# ── Subprocess Helper ──

class XpostResult:
    """Wrapper around subprocess result with convenience methods."""

    def __init__(self, completed: subprocess.CompletedProcess):
        self._proc = completed
        self.returncode = completed.returncode
        self.stdout = completed.stdout
        self.stderr = completed.stderr

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def json(self):
        """Parse stdout as JSON. Returns the first JSON object found."""
        text = self.stdout.strip()
        if not text:
            return None
        # The script may print multiple JSON objects (one per tweet).
        # Try parsing the whole output first, then fall back to first object.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Find the first complete JSON object
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(text)
                return obj
            except json.JSONDecodeError:
                return None

    def json_all(self):
        """Parse stdout as a list of JSON objects (one per printed block)."""
        text = self.stdout.strip()
        if not text:
            return []
        objects = []
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            # Skip whitespace
            while idx < len(text) and text[idx] in " \t\n\r":
                idx += 1
            if idx >= len(text):
                break
            try:
                obj, end = decoder.raw_decode(text, idx)
                objects.append(obj)
                idx = end
            except json.JSONDecodeError:
                break
        return objects

    def has_error(self, *fragments: str) -> bool:
        """Check if stderr contains any of the given fragments."""
        stderr_lower = self.stderr.lower()
        return any(f.lower() in stderr_lower for f in fragments)

    def __repr__(self):
        status = "OK" if self.ok else f"FAIL({self.returncode})"
        return f"<XpostResult {status} stdout={len(self.stdout)}B stderr={len(self.stderr)}B>"


def _run_xpost(*args: str, timeout: int = 30) -> XpostResult:
    """Run xpost.py with the given CLI arguments and return an XpostResult.

    If the process times out, returns an XpostResult with returncode=-1
    and a descriptive stderr instead of raising TimeoutExpired.
    """
    cmd = [sys.executable, str(SCRIPT)] + list(args)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
            cwd=str(ROOT_DIR),
        )
    except subprocess.TimeoutExpired as e:
        # Streaming commands may hang waiting for data -- treat timeout as a
        # non-fatal result so the test can decide how to handle it.
        fake = subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout=(e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            stderr=f"TimeoutExpired: command timed out after {timeout}s",
        )
        return XpostResult(fake)
    return XpostResult(proc)


@pytest.fixture(scope="session")
def xpost():
    """Provide the xpost runner function to all tests."""
    return _run_xpost


@pytest.fixture(scope="session")
def target_username():
    """Return the configurable target username for follow/mute/block tests."""
    username = os.environ.get("TEST_TARGET_USERNAME", "").strip()
    if not username:
        pytest.skip("TEST_TARGET_USERNAME not set in .env -- skipping social tests")
    return username.lstrip("@")
