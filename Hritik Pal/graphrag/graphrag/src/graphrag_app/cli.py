"""Streamlit launcher for GraphRAG."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Open the GraphRAG Streamlit interface in a browser window."""
    app_path = Path(__file__).with_name("streamlit_app.py")
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=false",
    ]
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
