from __future__ import annotations

import sys

from gemma_cli.cli import cli


def rewrite_slash(argv: list[str]) -> list[str]:
    """첫 번째 비-옵션 인자가 '/name' 형태면 'run name'으로 변환한다.

    예) ['gemma', '/commit'] -> ['gemma', 'run', 'commit']
        ['gemma', '/pr', '--base', 'develop'] -> ['gemma', 'run', 'pr', '--base', 'develop']
    """
    if len(argv) < 2:
        return argv
    out = list(argv)
    for i in range(1, len(out)):
        token = out[i]
        if token in ("--help", "-h", "--version"):
            return out
        if token.startswith("-"):
            continue
        if token.startswith("/") and len(token) > 1 and not token.startswith("//"):
            name = token[1:]
            return out[:i] + ["run", name] + out[i + 1 :]
        return out
    return out


def main() -> None:
    sys.argv = rewrite_slash(sys.argv)
    cli()


if __name__ == "__main__":
    main()
