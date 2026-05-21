# CLAUDE.md

이 파일은 Claude Code(claude.ai/code)가 이 저장소에서 작업할 때 참고하는 지침이다.
(gemma-cli **런타임**이 시스템 프롬프트에 덧붙이는 [`GEMMA.md`](GEMMA.md)와는 역할이 다르다.)

## 프로젝트 개요

`gemma-cli` — `gemma4`(MLX) 기반 로컬 개발 보조 CLI(Python 3.11+, Apple Silicon). 단일 명령어 `gemma`로
코드 리뷰·커밋/PR 메시지·리팩토링·분석·자유 질의를 한국어로 제공하고, `GEMMA.md`(프로젝트 지침)와
사용자 정의 **스킬**(`*.md`)을 지원한다.

- 스택: `click`, `mlx-lm`, `rich`, `pydantic`, `pyyaml` / 개발: `pytest`, `pytest-asyncio`
- 진입점: `gemma = gemma_cli.__main__:main` (pyproject.toml)
- 모든 모델 추론은 `mlx-lm`으로 **인프로세스(in-process)** 스트리밍 — 별도 서버 불필요. `mlx-lm`은 Apple Silicon 전용.

## 자주 쓰는 명령

```bash
# 테스트 (MLX 로드/생성을 conftest의 mlx_stub로 스텁 — 네트워크·모델 불필요)
.venv/bin/python -m pytest            # 또는: uv run pytest
.venv/bin/python -m pytest tests/test_skills.py -q

# CLI 직접 실행
.venv/bin/gemma --help
.venv/bin/gemma ask "질문"
```

## 구조

```
src/gemma_cli/
  __main__.py        # main() — rewrite_slash 후 cli() 호출
  cli.py             # SkillGroup(click.Group) + 빌트인 커맨드 등록
  commands/          # CLI 레이어 (review/commit/pr/refactor/analyze/ask/skills)
    _common.py       # make_client / stream_chat / load_cfg 등 공통
    skills.py        # run(=skills_run), run_skill(), make_skill_command()
  services/          # 로직 레이어
    config.py        # Config / load_config / for_command (모델·온도 해석)
    skills.py        # Skill, discover_skills, find_skill, _parse_skill
    actions.py       # collect_input(입력 모드) / execute_action(액션)
    git_ops.py, mlx_client.py, renderer.py, session.py, instructions.py, ...
tests/               # mlx_stub 스텁, conftest fixtures: tmp_home / tmp_git_repo / mlx_stub
```

**원칙**: 새 명령어는 `commands/`, 공통/로직은 `services/`. CLI 레이어는 얇게, 로직은 services에.

## 스킬 시스템 (핵심)

스킬 = 마크다운 1개. frontmatter(`name`, `description`, `action`, `input`, `base`) + 본문(`{{input}}`·`{{arg키}}` 치환).

- **탐색 위치** (`discover_skills`): 전역 `~/.config/gemma-cli/skills/*.md` + 프로젝트 `./.gemma/skills/*.md`(cwd→상위 트리). 프로젝트가 동명 스킬을 덮어쓴다.
- **자동 연동(1급 커맨드)**: `cli.py`의 `SkillGroup`이 발견된 스킬을 동적으로 Click 커맨드로 노출한다.
  `.md`만 떨어뜨리면 코드 수정 없이 `gemma <이름>` / `gemma /<이름>`로 실행되고 `gemma --help`에도 나타난다.
  - 빌트인과 이름이 겹치면(`commit`/`pr`) **빌트인 우선**. 스킬 쪽은 `/commit`(→`run commit`)로 호출.
  - `__main__.py`의 `rewrite_slash`가 `/name` → `run name`으로 라우팅(슬래시 네임스페이스 보존).
  - `run`(빌트인)과 동적 스킬 커맨드는 `commands/skills.py:run_skill()` 로직을 공유한다.
- **견고성**: `_parse_skill`은 읽을 수 없는 파일(끊긴 심링크 등)을 `None`으로 건너뛴다 — 스킬 하나의 문제가 전체 디스커버리/`--help`를 막지 않는다.
- **입력 모드**(`actions.collect_input`): `manual` / `staged-diff` / `branch-diff` / `commit-context` / `branch-or-files`.
- **액션**(`actions.execute_action`): `print` / `git-commit` / `gh-pr`.
- 기본 제공 프로젝트 스킬: `.gemma/skills/`의 `commit`, `pr`, `jira`(일감 본문), `qa`(QA 리뷰).

## 모델 설정

`~/.config/gemma-cli/config.yaml`(XDG). `Config.for_command(name)` = 명령별 override 있으면 그것, 없으면 기본값. 반환값은 `(model, temperature, max_tokens)` 3-튜플.

- `model`은 **MLX 모델 경로**(HuggingFace 저장소 이름 또는 로컬 MLX 디렉터리). 처음 쓰는 모델은 HF에서 자동 다운로드된다.
- **⚠️ 반드시 텍스트 전용 모델**: `mlx-lm`은 텍스트 전용 모델만 로드한다. `gemma-4`/`gemma-3n`의 e4b·26b, `gemma-3`의 4b/12b/27b는 모두 멀티모달(VLM)이라 `Received N parameters not in model: language_model....` 오류로 **로드 실패**한다. 반드시 텍스트 전용 변형(`-lm` 또는 `-text-`)을 쓴다. 실제 로드·생성 검증된 값: `mlx-community/gemma-3n-E4B-it-lm-4bit`, `mlx-community/gemma-3-text-27b-it-4bit`, `mlx-community/gemma-3-1b-it-4bit`. (멀티모달까지 쓰려면 `mlx-vlm`이 별도로 필요 — 현재 CLI는 텍스트 전용.)
- **현재 권장 구성**: 기본 모델 `mlx-community/gemma-3-text-27b-it-4bit`, `ask`만 `mlx-community/gemma-3n-E4B-it-lm-4bit` override.
  → `review/commit/pr/refactor/analyze/run·스킬`은 27b, `ask`는 e4b.
- 스킬 실행은 `make_client(cfg, "run")`을 쓰므로 `run` 키(없으면 기본 `model`)를 따른다.
- `max_tokens`(기본 2048)는 생성 토큰 상한 — ollama와 달리 MLX는 명시적 상한이 필요하다. 명령별 override 가능.
- **주의**: 코드 기본값(`config.py`의 `Config.model`)은 `mlx-community/gemma-3n-E4B-it-lm-4bit`이며 `test_config.py`가 이를 검증한다 — 코드 기본값을 바꾸면 테스트가 깨진다.
- **MLX 스레드 제약**: 스트림이 스레드-로컬이라 `mlx_client.chat_stream`은 모델 로드와 `stream_generate`를 같은(메인) 스레드에서 수행한다. `asyncio.to_thread`로 로드를 분리하면 `There is no Stream(gpu, N) in current thread` 오류가 난다.
- **특수 토큰 처리**: gemma는 `<end_of_turn>`을 EOS로 등록하지 않아 출력에 특수 토큰이 새므로 `mlx_client._split_at_stop`이 정지 마커에서 잘라낸다.

## 컨벤션

- 응답·주석·문서·테스트 이름은 **한국어**.
- 모든 MLX 추론은 테스트에서 `mlx_stub` 픽스처(conftest)로 스텁한다 — `_load_model`/`_stream_tokens`를 몽키패치해 네트워크·모델 없이 동작. `mlx_stub.response`로 출력 지정, `mlx_stub.last_user_content()`로 전달 메시지 검증.
- 스킬/명령 동작을 바꾸면 `tests/`에 대응 테스트를 추가하고 `pytest` 전체 통과를 확인한다.
- 커밋은 사용자가 요청할 때만. `main`에서 작업 중이면 먼저 브랜치를 분리한다.
