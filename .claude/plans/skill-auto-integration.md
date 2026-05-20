# 스킬 자동 연동(1급 커맨드화) 구현 계획

## 개요
- **목적**: `.gemma/skills/<name>.md`(또는 전역 스킬)를 추가하면 코드 수정 없이 `gemma <name>` / `gemma /<name>`로 즉시 호출되고 `gemma --help`에도 노출되도록 한다.
- **범위(포함)**: 스킬의 동적 Click 커맨드 등록, 스킬 실행 로직 재사용 함수화, 단위 테스트, business-expense-dinner 라이브 검증.
- **범위(제외)**: 새 input/action 종류 추가, 원격(remote) 스킬, 설정 스키마 변경.

## 현재 상태(조사 요약)
- 관련 파일:
  - `src/gemma_cli/__main__.py` — `rewrite_slash`(`/name` → `run name`)
  - `src/gemma_cli/cli.py` — `click.group()` + 빌트인 8종 등록
  - `src/gemma_cli/commands/skills.py` — `skills_list`(`skills`), `skills_run`(`run`)
  - `src/gemma_cli/services/skills.py` — `discover_skills`, `find_skill`, `Skill`
  - `src/gemma_cli/services/actions.py` — `collect_input`, `execute_action`
- 현재 패턴: 빌트인은 `cli.add_command()`로 정적 등록. 스킬은 `run`을 통해서만 실행되며 `--help`/명령 목록에 안 보임.
- 의존성: click 8.x(Group 커스터마이즈), 기존 `make_client(cfg, "run")` 모델 오버라이드.
- 주의점: `commit`/`pr`은 빌트인과 동명 스킬이 공존 → **빌트인 우선** 정책 유지 필요. `/commit`은 스킬을 실행해야 하므로 `rewrite_slash`의 `/name → run name`는 유지.

## 구현 단계

### Phase 1: 스킬 실행 로직 함수화 (선행)
- `commands/skills.py`에서 `skills_run` 본문을 `run_skill(skill, *, input_path, args_raw, input_text, base)`로 추출.
- `skills_run`(`run` 커맨드)은 디스커버리 + not-found 처리 후 `run_skill` 호출.
- 산출물: 동작 동일, 로직 단일화.

### Phase 2: 스킬 → 1급 커맨드 동적 등록
- `cli.py`에 `SkillGroup(click.Group)` 정의:
  - `list_commands`: 빌트인 ∪ 발견된 스킬 이름(정렬).
  - `get_command`: 빌트인 우선; 없으면 `find_skill` → 동적 커맨드 생성.
- `make_skill_command(skill)`(commands/skills.py): `run`과 동일 옵션(`input_path`, `--arg`, `--input`, `--base`)을 갖는 Click 커맨드를 만들어 `run_skill` 호출. `short_help`에 `[스킬] <description>` 표기.
- 산출물: `gemma jira`, `gemma jira --base develop`, `gemma --help`에 jira 노출.

### Phase 3: 슬래시 라우팅 유지/검증
- `rewrite_slash`는 `/name → run name` 유지(동명 스킬 네임스페이스 보존, 기존 테스트 grün).
- 산출물: `/commit`은 스킬, `commit`은 빌트인 — 기존 의미 보존.

### Phase 4: 단위 테스트 (gemma-cli)
- `tests/test_skill_commands.py` 신규:
  - 스킬이 `--help`/`list_commands`에 노출
  - `gemma <skill>` 직접 호출(ollama mock)로 실행
  - 빌트인 우선(commit 동명 스킬 존재해도 `gemma commit`은 빌트인)
  - 미존재 커맨드는 에러
- 기존 테스트 전부 통과 유지.

### Phase 5: 요구사항 #2 — jira.md 제거 + 외부 프로젝트 검증
- `business-expense-dinner/.gemma/skills/jira.md` 추가(이식형 사본).
- business-expense-dinner에 신규 브랜치 생성 후 코드 추가/수정(도메인 유틸 + vitest) → 커밋.
- 그 디렉터리에서 `gemma /jira` 라이브 실행(ollama 26b)으로 자동 연동 검증.
- gemma-cli `.gemma/skills/jira.md` 삭제(요구사항). README의 jira 관련 서술 최소 갱신.
- 변경사항을 배경 → 기술 스펙 → 변경사항 → 설계 → 테스트 순서로 정리·공유.

## 수정 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `src/gemma_cli/commands/skills.py` | 수정 | `run_skill`/`make_skill_command` 추가, `skills_run` 리팩토링 |
| `src/gemma_cli/cli.py` | 수정 | `SkillGroup` 도입, group cls 교체 |
| `tests/test_skill_commands.py` | 생성 | 동적 등록/우선순위/노출 테스트 |
| `.gemma/skills/jira.md` | 삭제 | 요구사항 #2 |
| `README.md` | 수정 | 1급 커맨드 모델 + jira 예시 위치 갱신 |
| `business-expense-dinner/.gemma/skills/jira.md` | 생성 | 외부 프로젝트 검증용 |
| `business-expense-dinner/src/lib/expense.ts` + 테스트 | 생성 | 검증용 코드 추가 |

## 인수 조건
- [ ] `gemma --help`에 발견된 스킬이 노출된다.
- [ ] `gemma <skill>`가 `gemma run <skill>`와 동일하게 동작한다.
- [ ] `gemma commit`은 빌트인, `gemma /commit`은 스킬(기존 의미 보존).
- [ ] 기존 + 신규 단위 테스트 전부 통과(`pytest -q`).
- [ ] business-expense-dinner에서 코드 추가 후 `gemma /jira`가 요약을 생성한다.
- [ ] gemma-cli `.gemma/skills/jira.md`가 삭제된다.

## 의존성 그래프
Phase 1 → Phase 2 → (Phase 3 검증) → Phase 4
Phase 5는 Phase 2 완료 후 가능(라이브 검증).
