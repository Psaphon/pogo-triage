import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from click.testing import CliRunner

from pogo_triage.cli import main


def test_help_lists_version():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output


def test_version_prints_metadata_version():
    result = CliRunner().invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == version("pogo-triage")


def _console_script() -> str:
    # Prefer the script next to this interpreter, so a stray install on PATH is never tested.
    local = Path(sys.executable).parent / "pogo-triage"
    found = str(local) if local.exists() else shutil.which("pogo-triage")
    assert found, "pogo-triage console script is not installed"
    return found


def test_installed_entry_point_help():
    result = subprocess.run([_console_script(), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "version" in result.stdout


def test_installed_entry_point_version():
    result = subprocess.run([_console_script(), "version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == version("pogo-triage")
