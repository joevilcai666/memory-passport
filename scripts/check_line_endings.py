"""Validate the Git contract for Unix shell scripts in this checkout."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


EXPECTED_SHEBANG = b"#!/usr/bin/env bash\n"


def git(*args: str, cwd: Path) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def tracked_shell_scripts(root: Path) -> list[str]:
    output = git("ls-files", "-z", "--", "*.sh", cwd=root)
    return [path.decode() for path in output.split(b"\0") if path]


def indexed_modes(root: Path, scripts: list[str]) -> dict[str, str]:
    output = git("ls-files", "--stage", "-z", "--", *scripts, cwd=root)
    modes: dict[str, str] = {}
    for entry in output.split(b"\0"):
        if not entry:
            continue
        metadata, path = entry.split(b"\t", maxsplit=1)
        modes[path.decode()] = metadata.split(maxsplit=1)[0].decode()
    return modes


def eol_attributes(root: Path, scripts: list[str]) -> dict[str, str]:
    output = git("check-attr", "-z", "eol", "--", *scripts, cwd=root)
    fields = output.split(b"\0")
    attributes: dict[str, str] = {}
    for index in range(0, len(fields) - 1, 3):
        path, _attribute, value = fields[index : index + 3]
        attributes[path.decode()] = value.decode()
    return attributes


def validate(root: Path) -> list[str]:
    scripts = tracked_shell_scripts(root)
    modes = indexed_modes(root, scripts)
    attributes = eol_attributes(root, scripts)
    errors: list[str] = []

    for relative_path in scripts:
        data = (root / relative_path).read_bytes()
        if b"\r" in data:
            errors.append(f"{relative_path}: contains CR/CRLF line endings")
        if not data.startswith(EXPECTED_SHEBANG):
            errors.append(
                f"{relative_path}: must start with #!/usr/bin/env bash followed by LF"
            )
        if modes.get(relative_path) != "100755":
            errors.append(
                f"{relative_path}: Git mode must be 100755, got "
                f"{modes.get(relative_path, 'untracked')}"
            )
        if attributes.get(relative_path) != "lf":
            errors.append(
                f"{relative_path}: Git eol attribute must be lf, got "
                f"{attributes.get(relative_path, 'unspecified')}"
            )

    return errors


def main() -> int:
    script_directory = Path(__file__).resolve().parent
    root = Path(
        git("rev-parse", "--show-toplevel", cwd=script_directory).decode().strip()
    )
    errors = validate(root)
    if errors:
        print("Unix script portability check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Unix script portability check passed ({len(tracked_shell_scripts(root))} files)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
