"""
ShellSage — AI-powered shell command assistant.
"""

import os
import argparse

from . import api, config
from .ui import (
    console, print_banner, print_command_result, print_error,
    print_success, print_info, print_history, print_config,
    print_help, print_rule, prompt_action, confirm, Thinking,
    C_PRIMARY, C_ACCENT, C_DIM,
)
from .clipboard import copy
from .runner import run_command

_last_command = ""
_last_query   = ""
_last_data    = {}


def build_parser():
    p = argparse.ArgumentParser(prog="shellsage", add_help=False)
    p.add_argument("query",           nargs="?")
    p.add_argument("--explain",       metavar="CMD")
    p.add_argument("--fix",           metavar="CMD")
    p.add_argument("--fix-error",     metavar="ERR", default="")
    p.add_argument("--refine",        metavar="HINT")
    p.add_argument("--run",           action="store_true")
    p.add_argument("--history",       action="store_true")
    p.add_argument("--search",        metavar="KW")
    p.add_argument("--clear-history", action="store_true")
    p.add_argument("--shell",         metavar="SH")
    p.add_argument("--no-copy",       action="store_true")
    p.add_argument("--json",          action="store_true")
    p.add_argument("--version",       action="store_true")
    p.add_argument("--help", "-h",    action="store_true")
    p.add_argument("--set",           metavar="K=V")
    p.add_argument("--get",           metavar="KEY")
    return p


def handle_result(data: dict, mode: str, query: str = "",
                  auto_run: bool = False, no_copy: bool = False):
    global _last_command, _last_query, _last_data
    _last_data    = data
    _last_command = data.get("command", "")
    _last_query   = query

    print_command_result(data, mode=mode)

    danger = data.get("danger_level", "safe")
    api.save_history(query=query, command=_last_command,
                     mode=mode, danger_level=danger)

    if auto_run:
        _do_run(_last_command, danger)
        return

    _interactive_action(_last_command, danger, no_copy=no_copy)


def _do_run(command: str, danger: str = "safe"):
    if danger == "dangerous":
        if not confirm("This command is DANGEROUS. Really run it?", default=False):
            print_info("Aborted.")
            return
    elif danger == "caution":
        if not confirm("This command requires caution. Run it?", default=True):
            print_info("Aborted.")
            return
    print_rule("running")
    exit_code, _ = run_command(command)
    print_rule()
    if exit_code == 0:
        print_success("Exited with code 0")
    else:
        print_error(f"Exited with code {exit_code}")


def _interactive_action(command: str, danger: str, no_copy: bool = False):
    choice = prompt_action(danger)
    if choice in ("c", "copy"):
        if no_copy:
            print_info("Clipboard disabled (--no-copy).")
        elif copy(command):
            print_success("Copied to clipboard!")
        else:
            print_error("Clipboard copy failed. Install xclip/xsel on Linux.")
    elif choice in ("r", "run"):
        _do_run(command, danger)


def run_generate(query: str, auto_run=False, no_copy=False):
    with Thinking("Generating command..."):
        data = api.generate_command(query)
    handle_result(data, mode="generate", query=query,
                  auto_run=auto_run, no_copy=no_copy)


def run_explain(command: str):
    with Thinking("Explaining command..."):
        data = api.explain_command(command)
    handle_result(data, mode="explain", query=command)


def run_fix(command: str, error: str = ""):
    with Thinking("Diagnosing and fixing..."):
        data = api.fix_command(command, error)
    handle_result(data, mode="fix", query=command)


def run_refine(hint: str):
    global _last_command, _last_query
    if not _last_command:
        print_error("No previous command to refine. Generate one first.")
        return
    with Thinking("Refining command..."):
        data = api.refine_command(_last_query, _last_command, hint)
    handle_result(data, mode="refine", query=hint)


def interactive_repl():
    print_banner()
    console.print(
        f"  [{C_DIM}]Describe what you want, or type "
        f"[/{C_DIM}][{C_ACCENT}]?[/{C_ACCENT}][{C_DIM}] for help.[/{C_DIM}]\n"
    )
    while True:
        try:
            raw = console.input(
                f"[{C_ACCENT}]sage[/{C_ACCENT}][{C_DIM}]›[/{C_DIM}] "
            ).strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{C_DIM}]Goodbye.[/{C_DIM}]")
            break

        if not raw:
            continue
        lower = raw.lower()

        if lower in ("exit", "quit", "q"):
            console.print(f"[{C_DIM}]Goodbye.[/{C_DIM}]")
            break
        elif lower in ("?", "help"):
            print_help()
        elif lower == "history":
            try:
                print_history(api.fetch_history(limit=20))
            except Exception as e:
                print_error(str(e))
        elif lower == "clear":
            os.system("clear" if os.name != "nt" else "cls")
            print_banner()
        elif lower == "config":
            print_config(config.load())
        elif lower.startswith("refine:"):
            hint = raw[7:].strip()
            if hint:
                try:
                    run_refine(hint)
                except Exception as e:
                    print_error(str(e))
            else:
                print_info("Usage: refine: <what to change>")
        elif lower.startswith("fix:"):
            err = raw[4:].strip()
            if _last_command:
                try:
                    run_fix(_last_command, err)
                except Exception as e:
                    print_error(str(e))
            else:
                print_info("No previous command to fix.")
        elif lower.startswith("explain:"):
            cmd = raw[8:].strip()
            if cmd:
                try:
                    run_explain(cmd)
                except Exception as e:
                    print_error(str(e))
            else:
                print_info("Usage: explain: <command>")
        elif lower.startswith("search:"):
            kw = raw[7:].strip()
            try:
                print_history(api.fetch_history(search=kw, limit=20))
            except Exception as e:
                print_error(str(e))
        else:
            try:
                run_generate(raw)
            except Exception as e:
                print_error(str(e))


def main():
    parser = build_parser()
    args, _ = parser.parse_known_args()

    if args.shell:
        os.environ["SHELL"] = args.shell

    if args.version:
        console.print("shellsage v1.0.0")
        return

    if args.help:
        print_help()
        return

    # config subcommand
    if args.query == "config":
        if args.set:
            try:
                k, v = args.set.split("=", 1)
                config.set_value(k.strip(), v.strip())
                print_success(f"Set {k.strip()} = {v.strip()}")
            except ValueError:
                print_error("Usage: --set key=value")
        elif args.get:
            console.print(f"  {args.get} = {config.get(args.get)}")
        else:
            print_config(config.load())
        return

    if args.history:
        try:
            print_history(api.fetch_history(limit=50))
        except Exception as e:
            print_error(str(e))
        return

    if args.search:
        try:
            print_history(api.fetch_history(search=args.search, limit=50))
        except Exception as e:
            print_error(str(e))
        return

    if args.clear_history:
        if confirm("Clear all history?", default=False):
            try:
                n = api.clear_history()
                print_success(f"Cleared {n} records.")
            except Exception as e:
                print_error(str(e))
        return

    if args.explain:
        try:
            run_explain(args.explain)
        except Exception as e:
            print_error(str(e))
        return

    if args.fix:
        try:
            run_fix(args.fix, args.fix_error)
        except Exception as e:
            print_error(str(e))
        return

    if args.refine:
        try:
            run_refine(args.refine)
        except Exception as e:
            print_error(str(e))
        return

    if args.query:
        try:
            run_generate(args.query, auto_run=args.run, no_copy=args.no_copy)
        except Exception as e:
            print_error(str(e))
        return

    interactive_repl()


if __name__ == "__main__":
    main()
