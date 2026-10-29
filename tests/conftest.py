"""Test-wide setup. Runs before any test module imports ``config``."""
import os
import tempfile

# The smoke test runs app.py, which attaches a file handler to the root logger; without this every later test's
# validation messages (made from the made-up data in fixtures.py) would land in the real logs/app.log.
os.environ.setdefault("TUI_LOG_DIR", tempfile.mkdtemp(prefix="tui_test_logs_"))
