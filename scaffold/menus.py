"""Inline "pretty menus" for the interactive wizard (npx create-* style).

Questions and arrow-key select menus are printed in the normal terminal
scrollback; each block redraws in place while you interact and collapses to
a single ``✔ question › answer`` line once answered. Nothing takes over the
screen, so the whole session stays readable.

Used when ``scaffold`` runs with no arguments on a TTY; when stdin/stdout
are pipes (or termios is unavailable) :func:`scaffold.interactive.run_wizard`
falls back to plain line prompts.

Keys
----
    ↑↓ / jk      move the cursor
    Enter        confirm (single) / finish selecting (multi)
    space        select the option under the cursor (multi)
    1-9          pick / toggle that option instantly
    q / Esc      cancel the wizard
    Ctrl+C / D   cancel the wizard
"""

from __future__ import annotations

import argparse
import os
import re
import select
import shutil
import sys
from pathlib import Path

from scaffold.interactive import TYPE_ORDER, Cancelled, validate_name
from scaffold.store import Store
from scaffold.structure import ProjectBuilder

try:
    import termios
    import tty

    AVAILABLE = True
except ImportError:  # pragma: no cover - non-POSIX (e.g. bare Windows)
    termios = None
    tty = None
    AVAILABLE = False


# --------------------------------------------------------------------------
# Colors / glyphs
# --------------------------------------------------------------------------

def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):  # pragma: no cover - closed stdout
        return False


def _sgr(*codes: str) -> str:
    if not _color_enabled():
        return ""
    return "\033[" + ";".join(codes) + "m"


def _paint(text: str, *codes: str) -> str:
    if not _color_enabled():
        return text
    return _sgr(*codes) + text + _sgr("0")


def _unicode_ok() -> bool:
    encoding = getattr(sys.stdout, "encoding", "") or "utf-8"
    try:
        "✔ ✗ ❯ › ↑ ↓".encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return False
    return True


if _unicode_ok():
    OK_GLYPH, ERR_GLYPH, CURSOR_GLYPH, SEP_GLYPH, UP_GLYPH, DOWN_GLYPH = (
        "✔", "✗", "❯", "›", "↑", "↓",
    )
else:  # pragma: no cover - legacy/ascii terminals
    OK_GLYPH, ERR_GLYPH, CURSOR_GLYPH, SEP_GLYPH, UP_GLYPH, DOWN_GLYPH = (
        "+", "x", ">", ">", "^", "v",
    )


# --------------------------------------------------------------------------
# Screen helpers
# --------------------------------------------------------------------------

def _draw(lines: list[str]) -> None:
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def _erase(count: int) -> None:
    """Erase a block of *count* lines just drawn (cursor sits below it)."""
    if count:
        sys.stdout.write("\033[" + str(count) + "A\033[J")
        sys.stdout.flush()


def _erase_prompt_line(prompt: str = "", answer: str = "") -> None:
    """Erase the line(s) the last ``input()`` prompt + echo occupied.

    *prompt*/*answer* are used to account for echoes that wrapped onto an
    extra line (long project names on narrow terminals).
    """
    visible = re.sub(r"\033\[[0-9;]*m", "", prompt) + answer
    cols = max(shutil.get_terminal_size().columns, 1)
    lines = (max(len(visible), 1) - 1) // cols + 1
    sys.stdout.write("\033[" + str(lines) + "A\033[2K\r")
    sys.stdout.flush()


def _question(title: str) -> str:
    return _paint("?", "36") + " " + _paint(title, "1")


def _collapsed(title: str, answer: str) -> str:
    return (
        _paint(OK_GLYPH, "32")
        + " "
        + _paint(title, "1")
        + " "
        + _paint(SEP_GLYPH, "2")
        + " "
        + _paint(answer, "36")
    )


def _hint(text: str) -> str:
    return _paint("  (" + text + ")", "2")


def _error(text: str) -> str:
    return _paint(ERR_GLYPH + " " + text, "31")


def _dim(text: str) -> str:
    return _paint(text, "2")


# --------------------------------------------------------------------------
# Terminal input
# --------------------------------------------------------------------------

class Unavailable(Exception):
    """Raised when this terminal cannot run the inline menus."""


class _RawTerminal:
    """Put the tty in cbreak mode for one menu, restoring it afterwards.

    ``tty.setcbreak`` only clears ECHO/ICANON, so ISIG stays enabled and
    Ctrl+C raises KeyboardInterrupt while a menu is on screen. termios is
    restored before any ``input()`` call runs again.
    """

    def __init__(self, fd: int):
        self.fd = fd
        self.saved = None

    def __enter__(self) -> int:
        self.saved = termios.tcgetattr(self.fd)
        # TCSADRAIN, not setcbreak()'s TCSAFLUSH default: keys the user
        # typed ahead while the previous prompt ran must survive the switch.
        tty.setcbreak(self.fd, termios.TCSADRAIN)
        return self.fd

    def __exit__(self, *exc) -> bool:
        if self.saved is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
            self.saved = None
        return False


def _read_key(fd: int) -> str | None:
    """Read one key press; returns a symbolic name or None for unknown keys."""
    try:
        data = os.read(fd, 1)
    except OSError:
        return None
    if not data:
        raise Cancelled from None
    ch = data[0]

    if ch == 0x1B:  # ESC: lone key or start of a CSI sequence
        if select.select([fd], [], [], 0.05)[0]:
            rest = os.read(fd, 1)
            if rest != b"[":
                return None
            final = os.read(fd, 1)
            return {
                b"A": "up",
                b"B": "down",
                b"C": "right",
                b"D": "left",
            }.get(final)
        return "esc"

    if ch in (0x0D, 0x0A):
        return "enter"
    if ch == 0x20:
        return "space"
    if ch in (0x03, 0x04):  # Ctrl+C / Ctrl+D (latter in cbreak mode)
        raise Cancelled from None
    if ch in (ord("q"), ord("Q")):
        return "q"
    if ch == ord("j"):
        return "down"
    if ch == ord("k"):
        return "up"
    if 0x31 <= ch <= 0x39:
        return chr(ch)
    return None


# --------------------------------------------------------------------------
# Menus
# --------------------------------------------------------------------------

def _single_lines(
    title: str,
    options: list[str],
    cursor: int,
    checked: set[int],  # unused: keeps both renderers the same shape
) -> list[str]:
    lines = [_question(title)]
    for i, option in enumerate(options):
        marker = _paint(CURSOR_GLYPH, "32", "1") if i == cursor else " "
        lines.append(f"{marker} {i + 1}. {option}")
    lines.append(_hint(
        f"{UP_GLYPH}{DOWN_GLYPH}/jk move · enter select · 1-{len(options)} quick · q quit"
    ))
    return lines


def _multi_lines(
    title: str,
    options: list[str],
    cursor: int,
    checked: set[int],
) -> list[str]:
    lines = [_question(title)]
    for i, option in enumerate(options):
        marker = _paint(CURSOR_GLYPH, "32", "1") if i == cursor else " "
        box = f"[{'x' if i in checked else ' '}]"
        box = _paint(box, "32") if i in checked else _paint(box, "2")
        lines.append(f"{marker} {box} {i + 1}. {option}")
    lines.append(_hint(
        f"space/1-{len(options)} toggle · {UP_GLYPH}{DOWN_GLYPH}/jk move · enter confirm · q quit"
    ))
    return lines


def _menu(
    title: str,
    options: list[str],
    *,
    multi: bool = False,
) -> int | list[int]:
    """Draw a select menu and return the chosen index (or indices)."""
    if not options:
        raise ValueError(f"_menu('{title}') called without options")

    cursor = 0
    checked: set[int] = set()
    render = _multi_lines if multi else _single_lines

    fd = sys.stdin.fileno()
    lines: list[str] = []
    drawn = False
    try:
        # cbreak is held for the whole menu: re-entering it per key would
        # re-enable canonical line buffering (and echo) between reads.
        with _RawTerminal(fd):
            while True:
                lines = render(title, options, cursor, checked)
                _draw(lines)
                drawn = True
                key = _read_key(fd)
                _erase(len(lines))
                drawn = False

                if key in ("q", "esc"):
                    raise Cancelled from None
                if key is None or key in ("right", "left"):
                    continue
                if key == "up":
                    cursor = (cursor - 1) % len(options)
                elif key == "down":
                    cursor = (cursor + 1) % len(options)
                elif key == "enter":
                    if multi:
                        return sorted(checked)
                    return cursor
                elif key == "space":
                    if multi:
                        checked ^= {cursor}
                    else:
                        return cursor
                elif key.isdigit():
                    index = int(key) - 1
                    if not 0 <= index < len(options):
                        continue
                    if multi:
                        checked ^= {index}
                        cursor = index
                    else:
                        return index
    except (KeyboardInterrupt, Cancelled):
        # Ctrl+C raises KeyboardInterrupt (ISIG stays on in cbreak mode),
        # Ctrl+D / EOF raise Cancelled: drop the block before bailing out.
        if drawn:
            _erase(len(lines))
        raise Cancelled from None


def _ask_text(title: str, validate) -> str:
    """Line prompt that collapses to ``✔ title › value`` on success."""
    while True:
        prompt = f"{_question(title)} {_paint(SEP_GLYPH, '2')} "
        try:
            raw = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            raise Cancelled from None
        value = raw.strip()
        error = validate(value)
        if error is None:
            _erase_prompt_line(prompt, raw)
            print(_collapsed(title, value))
            return value
        # the error text carries the rejected value, so the prompt line can
        # go away instead of leaving a dangling "?" in the scrollback
        _erase_prompt_line(prompt, raw)
        print(_error(error))


# --------------------------------------------------------------------------
# Wizard
# --------------------------------------------------------------------------

def _validate_name(value: str) -> str | None:
    if not value:
        return "The name cannot be empty"
    try:
        validate_name(value)
    except ValueError as e:
        return str(e)
    root = Path(value)
    if root.exists() and any(root.iterdir()):
        return f"Directory '{root}' already exists and is not empty"
    return None


def _ask_confirm() -> bool:
    prompt = (
        f"{_question('Create this project?')} "
        f"{_paint('(Y/n)', '2')} {_paint(SEP_GLYPH, '2')} "
    )
    while True:
        try:
            raw = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            raise Cancelled from None
        answer = raw.strip().lower()
        if answer in ("", "y", "yes"):
            _erase_prompt_line(prompt, raw)
            print(_collapsed("Create this project?", "yes"))
            return True
        if answer in ("n", "no"):
            _erase_prompt_line(prompt, raw)
            # ✔ means "question answered", the value says what was decided
            print(_collapsed("Create this project?", "no"))
            return False
        _erase_prompt_line(prompt, raw)
        print(_error("Please answer 'y' or 'n'"))


def run() -> argparse.Namespace | None:
    """Ask the questions with inline menus; None means cancelled."""
    if not AVAILABLE:
        raise Unavailable("termios/tty are not available on this platform")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise Unavailable("stdin/stdout is not a terminal")

    try:
        name = _ask_text("Project name", _validate_name)

        types = [t.value for t in TYPE_ORDER]
        # single-select menus always return a plain index
        ptype = TYPE_ORDER[_menu("Project type", types)]  # type: ignore[arg-type]
        print(_collapsed("Project type", ptype.value))

        builder = ProjectBuilder(root=Path(name), project_type=ptype)
        _, _, struct_deps = builder.structure()
        fixed = [d.name for d in struct_deps if d.required]
        optional = [d.name for d in struct_deps if not d.required]

        selected: list[str] = []
        if optional:
            picked = _menu("Optional dependencies", optional, multi=True)
            selected = [optional[i] for i in picked]
            print(_collapsed("Optional dependencies", ", ".join(selected) or "(none)"))
        else:
            print(_dim(f"Type '{ptype.value}' has no optional dependencies"))

        pool = [k for k in Store().keys() if k not in set(fixed) | set(selected)]
        extra: list[str] = []
        if pool:
            picked = _menu("Extra dependencies", pool, multi=True)
            extra = [pool[i] for i in picked]
            print(_collapsed("Extra dependencies", ", ".join(extra) or "(none)"))

        chosen = selected + extra
        deps = fixed + chosen

        print(_dim(f"  location: {Path(name)}"))
        print(_dim(f"  will fetch: {', '.join(deps) if deps else '(none)'}"))

        if not _ask_confirm():
            print("[INFO] Cancelled")
            return None
    except (Cancelled, KeyboardInterrupt):
        print("[INFO] Cancelled")
        return None

    return argparse.Namespace(
        name=name,
        type=ptype.value,
        deps=",".join(chosen) if chosen else None,
    )
