"""Console-script wrapper that runs the Streamlit app."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Entry point for `spatial-grid-ui` — invokes `streamlit run` on ui_app.py."""
    try:
        import streamlit  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "streamlit is not installed.\n"
            "Install UI extras with:  pip install -e .[ui]\n"
        )
        sys.exit(1)

    app_path = Path(__file__).resolve().parent / "ui_app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), *sys.argv[1:]]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
