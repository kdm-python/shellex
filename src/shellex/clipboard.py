"""Copy text using the clipboard tools provided by the desktop environment."""

import os
import shutil
import subprocess
import sys

from .errors import ShellexError


def copy_text(text: str) -> None:
    """Copy exact text to the system clipboard, or report an actionable error."""
    if sys.platform == "darwin":
        candidates = [("pbcopy", [])]
    elif sys.platform == "win32":
        candidates = [("clip.exe", [])]
    else:
        candidates = []
        if os.environ.get("WAYLAND_DISPLAY"):
            candidates.append(("wl-copy", []))
        if os.environ.get("DISPLAY"):
            candidates.extend([("xclip", ["-selection", "clipboard"]), ("xsel", ["--clipboard", "--input"])])

    failures = []
    for program, arguments in candidates:
        executable = shutil.which(program)
        if not executable:
            continue
        try:
            # clip.exe recognises UTF-16 text by its BOM; other tools accept UTF-8.
            data = text.encode("utf-16" if sys.platform == "win32" else "utf-8")
            result = subprocess.run([executable, *arguments], input=data, capture_output=True, check=False)
        except OSError as exc:
            failures.append(f"{program}: {exc}")
            continue
        if result.returncode == 0:
            return
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        failures.append(f"{program}: {detail or 'exit status ' + str(result.returncode)}")

    if failures:
        raise ShellexError("Could not copy to clipboard: " + "; ".join(failures))
    raise ShellexError("No clipboard tool available. Use a graphical session and install wl-copy, xclip or xsel on Linux (pbcopy on macOS, clip.exe on Windows).")
