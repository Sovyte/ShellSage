"""Runs shell commands and streams output."""

import subprocess
import os
import sys
from . import config


def run_command(command: str) -> tuple:
    shell    = config.get_shell()
    shell_path = _resolve_shell(shell)
    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            executable=shell_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy(),
        )
        lines = []
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lines.append(line)
        proc.wait()
        return proc.returncode, "".join(lines)
    except Exception as e:
        return 1, str(e)


def _resolve_shell(shell: str) -> str:
    for path in [f"/bin/{shell}", f"/usr/bin/{shell}", f"/usr/local/bin/{shell}"]:
        if os.path.exists(path):
            return path
    return "/bin/sh"
