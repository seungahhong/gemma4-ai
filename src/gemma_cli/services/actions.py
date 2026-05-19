from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import click

from gemma_cli.services import approval, git_ops


_SCAN_IGNORED = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    "dist", "build", ".pytest_cache", ".next", ".turbo",
    ".idea", ".vscode", ".mypy_cache", ".ruff_cache",
}


def _is_git_repo_without_calling_git(cwd: Path | None = None) -> bool:
    cur = (cwd or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        if (d / ".git").exists():
            return True
    return False


def _scan_workspace_files(
    root: Path,
    *,
    max_file_size: int = 50_000,
    total_cap: int = 80_000,
) -> tuple[list[str], str]:
    file_list: list[str] = []
    chunks: list[str] = []
    used = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or set(p.parts) & _SCAN_IGNORED:
            continue
        rel = p.relative_to(root)
        file_list.append(str(rel))
        if used >= total_cap:
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size >= max_file_size:
            continue
        try:
            text = p.read_text(errors="replace")
        except OSError:
            continue
        chunk = f"### {rel}\n```\n{text}\n```"
        if used + len(chunk) > total_cap:
            continue
        chunks.append(chunk)
        used += len(chunk)
    return file_list, "\n\n".join(chunks)


def collect_input(source: str, base: str = "main") -> str:
    if source == "manual":
        return ""
    if source == "staged-diff":
        if not git_ops.is_repo():
            raise click.UsageError("staged-diff 입력은 git 저장소에서만 사용 가능합니다.")
        diff = git_ops.staged_diff()
        if not diff.strip():
            raise click.UsageError("스테이징된 변경이 없습니다. `git add` 후 다시 시도해주세요.")
        return f"```diff\n{diff}\n```"
    if source == "branch-diff":
        if not git_ops.is_repo():
            raise click.UsageError("branch-diff 입력은 git 저장소에서만 사용 가능합니다.")
        diff = git_ops.branch_diff(base)
        log = git_ops.branch_log(base)
        if not diff.strip():
            raise click.UsageError(f"{base}와 비교한 변경사항이 없습니다.")
        return f"## 커밋 로그\n{log}\n\n## diff\n```diff\n{diff}\n```"
    if source == "branch-or-files":
        if _is_git_repo_without_calling_git():
            diff = git_ops.branch_diff(base)
            log = git_ops.branch_log(base)
            if not diff.strip():
                raise click.UsageError(f"{base}와 비교한 변경사항이 없습니다.")
            return f"## 커밋 로그\n{log}\n\n## diff\n```diff\n{diff}\n```"
        cwd = Path.cwd()
        file_list, body = _scan_workspace_files(cwd)
        if not file_list:
            raise click.UsageError("현재 디렉터리에서 분석할 파일을 찾지 못했습니다.")
        listing = "\n".join(f"- {f}" for f in file_list)
        return (
            "## 컨텍스트\n"
            "git 저장소가 아니어서 현재 디렉터리의 파일 목록과 내용을 사용합니다.\n\n"
            f"## 작업 디렉터리\n{cwd}\n\n"
            f"## 파일 목록\n{listing}\n\n"
            f"## 파일 내용 (50KB 미만, 총 80KB 한도)\n{body}"
        )
    if source == "commit-context":
        if not git_ops.is_repo():
            raise click.UsageError("commit-context 입력은 git 저장소에서만 사용 가능합니다.")
        diff = git_ops.staged_diff()
        if not diff.strip():
            diff = git_ops.unstaged_diff()
            if not diff.strip():
                raise click.UsageError("변경사항이 없습니다. `git add` 후 다시 시도해주세요.")
            scope_note = "(스테이징된 변경 없음 — 전체 변경 기준)"
        else:
            scope_note = "(스테이징된 변경 기준)"
        branch = git_ops.current_branch() or "(unknown)"
        log = git_ops.recent_log(10)
        return (
            f"## 현재 브랜치\n{branch}\n\n"
            f"## 최근 커밋 (10개)\n```\n{log}```\n\n"
            f"## 대상 diff {scope_note}\n```diff\n{diff}\n```"
        )
    raise click.UsageError(f"알 수 없는 input 소스: {source}")


def execute_action(action: str, output: str) -> int:
    if action == "print":
        return 0
    if action == "git-commit":
        return _do_git_commit(output)
    if action == "gh-pr":
        return _do_gh_pr(output)
    click.secho(f"알 수 없는 action: {action}", fg="yellow")
    return 0


def _do_git_commit(message: str) -> int:
    message = message.strip()
    if not message:
        click.echo("생성된 메시지가 비어 있습니다.")
        return 1
    click.echo()
    click.secho("=== 생성된 커밋 메시지 ===", fg="cyan")
    click.echo(message)
    click.echo()
    decision = approval.prompt_yne("이 메시지로 커밋할까요?")
    if decision == "edit":
        message = approval.edit_in_editor(message, suffix=".gitcommit").strip()
        if not message:
            click.echo("메시지가 비어 있어 취소합니다.")
            return 1
        click.secho("=== 편집된 메시지 ===", fg="cyan")
        click.echo(message)
        decision = approval.prompt_yne("이대로 커밋할까요?")
    if decision != "yes":
        click.echo("취소되었습니다.")
        return 0
    try:
        git_ops.commit(message)
        click.secho("✓ 커밋 완료", fg="green")
        return 0
    except git_ops.GitError as e:
        click.secho(f"커밋 실패: {e}", fg="red", err=True)
        return 1


def _split_title_body(text: str) -> tuple[str, str]:
    lines = text.strip().splitlines()
    title = ""
    body_lines: list[str] = []
    state = "title"
    for line in lines:
        if state == "title":
            if line.upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()
                state = "wait_sep"
            elif line.strip() == "---":
                state = "body"
        elif state == "wait_sep":
            if line.strip() == "---":
                state = "body"
        else:
            body_lines.append(line)
    return title, "\n".join(body_lines).strip()


def _do_gh_pr(output: str) -> int:
    title, body = _split_title_body(output)
    if not title:
        click.secho("PR 제목 추출 실패. 원본 출력:", fg="yellow")
        click.echo(output)
        return 1
    click.echo()
    click.secho("=== PR 제목 ===", fg="cyan")
    click.echo(title)
    click.secho("=== PR 본문 ===", fg="cyan")
    click.echo(body)
    click.echo()
    decision = approval.prompt_yne("이 내용으로 PR을 생성할까요?")
    if decision == "edit":
        edited = approval.edit_in_editor(f"{title}\n---\n{body}", suffix=".md")
        parts = edited.split("\n---\n", 1)
        if len(parts) == 2:
            title, body = parts[0].strip(), parts[1].strip()
        decision = approval.prompt_yne("이대로 PR을 생성할까요?")
    if decision != "yes":
        click.echo("취소되었습니다.")
        return 0
    if shutil.which("gh") is None:
        click.secho("`gh` CLI가 설치되어 있지 않습니다. 수동으로 PR을 생성해주세요.", fg="yellow")
        click.echo(f"제목: {title}")
        click.echo("본문:")
        click.echo(body)
        return 0
    res = subprocess.run(
        ["gh", "pr", "create", "--title", title, "--body", body],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        click.secho(f"gh pr create 실패: {res.stderr.strip()}", fg="red", err=True)
        return 1
    click.secho(res.stdout.strip(), fg="green")
    return 0
