"""
UI module — all Rich-powered terminal output for ShellSage.
Cyberpunk aesthetic: cyan / magenta / yellow on dark.
"""

import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.markup import escape
from rich import box

console = Console()

C_PRIMARY = "bright_cyan"
C_ACCENT  = "bright_magenta"
C_WARN    = "bright_yellow"
C_DANGER  = "bright_red"
C_SUCCESS = "bright_green"
C_DIM     = "grey50"
C_CMD     = "bold bright_white"

DANGER_COLORS = {"safe": C_SUCCESS, "caution": C_WARN, "dangerous": C_DANGER}
DANGER_ICONS  = {"safe": "✓", "caution": "⚠", "dangerous": "✗"}

BANNER = r"""
  ___ _        _ _ ___
 / __| |_  ___| | / __| __ _ __ _ ___
 \__ \ ' \/ -_) | \__ \/ _` / _` / -_)
 |___/_||_\___|_|_|___/\__,_\__, \___|
                              |___/
"""


def print_banner():
    for i, line in enumerate(BANNER.strip().split("\n")):
        color = C_PRIMARY if i % 2 == 0 else C_ACCENT
        console.print(f"[{color}]{escape(line)}[/{color}]")
    console.print(
        f"\n  [{C_DIM}]AI shell assistant · [{C_DIM}][{C_ACCENT}]?[/{C_ACCENT}]"
        f"[{C_DIM}] for help[/{C_DIM}]\n"
    )


class Thinking:
    def __init__(self, label: str = "Thinking..."):
        self._label = label
        self._live  = None

    def __enter__(self):
        self._live = Live(
            Spinner("dots2", text=f"[{C_PRIMARY}] {self._label}[/{C_PRIMARY}]"),
            console=console,
            refresh_per_second=10,
            transient=True,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *a):
        self._live.__exit__(*a)


def print_command_result(data: dict, mode: str = "generate"):
    command    = data.get("command", "")
    danger     = data.get("danger_level", "safe")
    danger_rsn = data.get("danger_reason", "")
    breakdown  = data.get("breakdown", [])
    alts       = data.get("alternatives", [])
    explanation = (
        data.get("explanation")
        or data.get("summary")
        or data.get("what_changed")
        or ""
    )

    danger_color  = DANGER_COLORS.get(danger, C_SUCCESS)
    border_color  = {"safe": C_PRIMARY, "caution": C_WARN, "dangerous": C_DANGER}.get(danger, C_PRIMARY)

    cmd_text = Text()
    cmd_text.append("$ ", style=C_DIM)
    cmd_text.append(command, style=C_CMD)

    console.print()
    console.print(Panel(
        Align.left(cmd_text),
        border_style=border_color,
        padding=(0, 2),
        title=f"[{C_ACCENT}] command [/{C_ACCENT}]",
        title_align="left",
    ))

    if explanation:
        console.print(f"  [{C_DIM}]→[/{C_DIM}] [{C_PRIMARY}]{escape(explanation)}[/{C_PRIMARY}]")

    if danger != "safe":
        icon = DANGER_ICONS.get(danger, "⚠")
        console.print(
            f"\n  [{danger_color}]{icon} {danger.upper()}[/{danger_color}]"
            + (f"  [{C_DIM}]{escape(danger_rsn)}[/{C_DIM}]" if danger_rsn else "")
        )

    if breakdown:
        console.print()
        t = Table(
            show_header=True,
            header_style=f"bold {C_ACCENT}",
            box=box.SIMPLE,
            padding=(0, 2),
            border_style=C_DIM,
        )
        t.add_column("Part",         style=C_CMD,     no_wrap=True)
        t.add_column("What it does", style=C_PRIMARY)
        for item in breakdown:
            t.add_row(
                escape(str(item.get("part", ""))),
                escape(str(item.get("desc", ""))),
            )
        console.print(t)

    if alts:
        console.print(f"  [{C_DIM}]alternatives:[/{C_DIM}]")
        for alt in alts:
            console.print(f"    [{C_DIM}]·[/{C_DIM}] [{C_PRIMARY}]{escape(str(alt))}[/{C_PRIMARY}]")

    if mode == "fix":
        for label, color, key in [
            ("✗ was wrong", C_WARN,    "what_was_wrong"),
            ("✓ fixed",     C_SUCCESS, "what_changed"),
            ("💡 tip",      C_ACCENT,  "tip"),
        ]:
            val = data.get(key, "")
            if val:
                console.print(f"\n  [{color}]{label}:[/{color}] [{C_DIM}]{escape(val)}[/{C_DIM}]")

    if mode == "explain":
        if data.get("example_output"):
            console.print(f"\n  [{C_DIM}]example output:[/{C_DIM}] [{C_PRIMARY}]{escape(data['example_output'])}[/{C_PRIMARY}]")
        for uc in data.get("use_cases", []):
            console.print(f"    [{C_DIM}]·[/{C_DIM}] {escape(uc)}")

    console.print()


def prompt_action(danger: str = "safe") -> str:
    actions = f"  [{C_ACCENT}][c][/{C_ACCENT}] [{C_DIM}]copy[/{C_DIM}]   " \
              f"[{C_ACCENT}][r][/{C_ACCENT}] [{C_DIM}]run[/{C_DIM}]   " \
              f"[{C_ACCENT}][q][/{C_ACCENT}] [{C_DIM}]back[/{C_DIM}]"
    console.print(actions)
    if danger == "dangerous":
        console.print(f"\n  [{C_DANGER}]⚠  Destructive command — type [bold]yes[/bold] to confirm run.[/{C_DANGER}]")
    console.print()
    try:
        return console.input(f"  [{C_PRIMARY}]›[/{C_PRIMARY}] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return "q"


def print_history(rows: list):
    if not rows:
        console.print(f"  [{C_DIM}]No history found.[/{C_DIM}]")
        return
    t = Table(
        show_header=True,
        header_style=f"bold {C_ACCENT}",
        box=box.SIMPLE_HEAVY,
        border_style=C_DIM,
        padding=(0, 1),
    )
    t.add_column("#",       style=C_DIM,    width=4)
    t.add_column("Mode",    style=C_ACCENT, width=9)
    t.add_column("Query",   style=C_PRIMARY, max_width=28)
    t.add_column("Command", style=C_CMD,    max_width=48)
    t.add_column("Danger",  width=10)
    t.add_column("Date",    style=C_DIM,    width=11)
    for i, row in enumerate(rows, 1):
        d = row.get("danger_level", "safe")
        t.add_row(
            str(i),
            row.get("mode", ""),
            escape((row.get("query") or "—")[:26]),
            escape(row.get("command", "")[:46]),
            f"[{DANGER_COLORS.get(d, C_DIM)}]{d}[/{DANGER_COLORS.get(d, C_DIM)}]",
            (row.get("created_at") or "")[:10],
        )
    console.print()
    console.print(Panel(t, title=f"[{C_ACCENT}] history [/{C_ACCENT}]",
                        border_style=C_PRIMARY, title_align="left"))
    console.print()


def print_config(cfg: dict):
    t = Table(box=box.SIMPLE, border_style=C_DIM, padding=(0, 2))
    t.add_column("Key",   style=C_ACCENT)
    t.add_column("Value", style=C_PRIMARY)
    for k, v in cfg.items():
        t.add_row(k, escape(str(v)))
    console.print(Panel(t, title=f"[{C_ACCENT}] config [/{C_ACCENT}]",
                        border_style=C_PRIMARY, title_align="left"))


def print_error(msg: str):
    console.print(f"\n  [{C_DANGER}]✗[/{C_DANGER}] [{C_DIM}]{escape(msg)}[/{C_DIM}]\n")


def print_success(msg: str):
    console.print(f"\n  [{C_SUCCESS}]✓[/{C_SUCCESS}] {escape(msg)}\n")


def print_info(msg: str):
    console.print(f"  [{C_DIM}]{escape(msg)}[/{C_DIM}]")


def print_rule(label: str = ""):
    console.print(Rule(label, style=C_DIM))


def confirm(prompt_text: str, default: bool = False) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        ans = console.input(
            f"  [{C_WARN}]?[/{C_WARN}] [{C_PRIMARY}]{escape(prompt_text)}[/{C_PRIMARY}] "
            f"[{C_DIM}]{hint}[/{C_DIM}] "
        ).strip().lower()
    except (KeyboardInterrupt, EOFError):
        return False
    return (ans in ("y", "yes")) if ans else default


def print_help():
    console.print()
    console.print(Panel(
        Text.from_markup(
            f"[{C_ACCENT}]shellsage[/{C_ACCENT}] [{C_DIM}]<query>[/{C_DIM}]               generate a command\n"
            f"[{C_ACCENT}]shellsage --explain[/{C_ACCENT}] [{C_DIM}]'<cmd>'[/{C_DIM}]     explain a command\n"
            f"[{C_ACCENT}]shellsage --fix[/{C_ACCENT}] [{C_DIM}]'<cmd>'[/{C_DIM}]         fix a broken command\n"
            f"[{C_ACCENT}]shellsage --run[/{C_ACCENT}]                    run generated command immediately\n"
            f"[{C_ACCENT}]shellsage --history[/{C_ACCENT}]                browse past commands\n"
            f"[{C_ACCENT}]shellsage --search[/{C_ACCENT}] [{C_DIM}]<kw>[/{C_DIM}]         search history\n"
            f"[{C_ACCENT}]shellsage --clear-history[/{C_ACCENT}]          wipe history\n"
            f"[{C_ACCENT}]shellsage config[/{C_ACCENT}]                   show config\n"
            f"[{C_ACCENT}]shellsage config --set[/{C_ACCENT}] [{C_DIM}]k=v[/{C_DIM}]      set a config value\n"
            f"\n[{C_DIM}]── Interactive REPL commands ──[/{C_DIM}]\n"
            f"  [{C_ACCENT}]refine:[/{C_ACCENT}] [{C_DIM}]<text>[/{C_DIM}]    tweak last command\n"
            f"  [{C_ACCENT}]fix:[/{C_ACCENT}] [{C_DIM}]<error>[/{C_DIM}]      fix last command\n"
            f"  [{C_ACCENT}]explain:[/{C_ACCENT}] [{C_DIM}]<cmd>[/{C_DIM}]    explain a command\n"
            f"  [{C_ACCENT}]search:[/{C_ACCENT}] [{C_DIM}]<kw>[/{C_DIM}]      search history\n"
            f"  [{C_ACCENT}]history[/{C_ACCENT}]             show history\n"
            f"  [{C_ACCENT}]config[/{C_ACCENT}]              show config\n"
            f"  [{C_ACCENT}]clear[/{C_ACCENT}]               clear screen\n"
            f"  [{C_ACCENT}]exit[/{C_ACCENT}] / [{C_ACCENT}]quit[/{C_ACCENT}]          exit ShellSage"
        ),
        title=f"[{C_ACCENT}] help [/{C_ACCENT}]",
        border_style=C_PRIMARY,
        title_align="left",
        padding=(1, 2),
    ))
    console.print()
