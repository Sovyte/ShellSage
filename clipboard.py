"""Cross-platform clipboard copy."""

import sys
import subprocess


def copy(text: str) -> bool:
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        elif sys.platform == "win32":
            subprocess.run(["clip"], input=text.encode(), check=True)
        else:
            for cmd in [
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
                ["wl-copy"],
            ]:
                try:
                    subprocess.run(cmd, input=text.encode(), check=True)
                    return True
                except FileNotFoundError:
                    continue
            return False
        return True
    except Exception:
        return False
