from __future__ import annotations

import click

from gemma_cli import __version__
from gemma_cli.commands import analyze as analyze_cmd
from gemma_cli.commands import ask as ask_cmd
from gemma_cli.commands import commit as commit_cmd
from gemma_cli.commands import pr as pr_cmd
from gemma_cli.commands import refactor as refactor_cmd
from gemma_cli.commands import review as review_cmd
from gemma_cli.commands import skills as skills_cmd


@click.group(help="gemma4 + ollama 기반 로컬 개발 보조 CLI")
@click.version_option(__version__, prog_name="gemma")
def cli() -> None:
    pass


cli.add_command(review_cmd.review)
cli.add_command(commit_cmd.commit)
cli.add_command(pr_cmd.pr)
cli.add_command(refactor_cmd.refactor)
cli.add_command(analyze_cmd.analyze)
cli.add_command(ask_cmd.ask)
cli.add_command(skills_cmd.skills_list)
cli.add_command(skills_cmd.skills_run)
