# 시작하기 — gemma-cli 환경 구축 가이드

이 문서는 **Apple Silicon macOS 환경에서 gemma-cli를 처음 설치하고 첫 명령을 성공적으로 실행할 때까지**의 모든 단계를 안내합니다. 명령어는 그대로 복사·붙여넣어 실행할 수 있으며, 각 단계마다 정상 동작을 확인하는 방법을 함께 적었습니다.

모델 추론은 [`mlx-lm`](https://github.com/ml-explore/mlx-lm)으로 **인프로세스(in-process)** 실행됩니다. ollama 같은 별도 서버나 데몬을 띄울 필요가 없고, 모델은 처음 사용할 때 HuggingFace에서 자동 다운로드됩니다.

소요 시간: 모델 다운로드 시간(약 5~10분)을 포함해 **15~25분**.

---

## 사전 점검 — 내 환경에서 시작해도 되나?

| 항목 | 요구 | 확인 명령 |
|------|------|-----------|
| OS | macOS 13+ | `sw_vers` |
| 칩 | **Apple Silicon (arm64)** — `mlx-lm`은 Apple Silicon 전용 | `uname -m` → `arm64` |
| 디스크 여유 | 5GB 이상(e4b) / 20GB 이상(27b) | `df -h ~` |
| 메모리 | 16GB 이상(e4b) / 32GB 이상(27b 권장) | `system_profiler SPHardwareDataType \| grep Memory` |
| 인터넷 | 모델 최초 다운로드용 (이후엔 오프라인 가능) | `curl -sI https://huggingface.co \| head -1` |

> `uname -m`이 `x86_64`(인텔 맥)거나 Linux라면 `mlx-lm`이 동작하지 않습니다. Apple Silicon 기기를 사용하세요.

기준에 못 미치면 더 가벼운 모델(`mlx-community/gemma-3n-E2B-it-4bit`)을 쓰는 것을 권장합니다.

---

## 1단계 — Python 3.11 이상 확인

```bash
python3 --version
```

**예상 출력:** `Python 3.11.x` ~ `Python 3.14.x`

### 버전이 낮거나 없다면

- **macOS:** `brew install python@3.12` (먼저 [Homebrew](https://brew.sh) 설치 필요)

설치 후 위 명령으로 다시 확인하세요.

---

## 2단계 — `uv` 설치 (Python 패키지 매니저)

`uv`는 pip보다 10~100배 빠른 Python 도구 관리자입니다. gemma-cli는 `uv`로 설치/실행하는 것을 기준으로 합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 후 셸을 새로 열거나:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 확인

```bash
uv --version
```

**예상 출력:** `uv 0.x.x (...)`

> **`uv: command not found`가 나오면?**
> `~/.local/bin`이 PATH에 없습니다. `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc` 실행하거나, `uv tool update-shell`로 자동 등록할 수 있습니다.

---

## 3단계 — gemma-cli 설치

프로젝트 디렉터리로 이동:

```bash
cd /Users/seungah.hong/workspace/gemma4-ai
```

> 자신의 경로에 맞게 바꿔주세요. git clone부터 한다면 `git clone <URL> gemma4-ai && cd gemma4-ai`.

설치하면 의존성으로 `mlx-lm`이 함께 들어옵니다(Apple Silicon에서만 설치됨). 별도의 모델 서버 설치는 필요 없습니다.

### 옵션 A — 글로벌 도구로 설치 (추천)

어디서든 `gemma` 명령으로 호출하고 싶다면:

```bash
uv tool install .
```

PATH에 `~/.local/bin/gemma` 가 생깁니다. `which gemma` 로 확인되면 성공.

PATH에 안 보이면:

```bash
uv tool update-shell
source ~/.zshrc   # 또는 새 터미널 열기
```

### 옵션 B — 개발 모드 (프로젝트 안에서만)

소스를 수정해가며 쓰려면:

```bash
uv sync --extra dev
```

이후 호출은 항상 `uv run gemma ...` 형태로.

### 확인

```bash
gemma --help          # 옵션 A
# 또는
uv run gemma --help   # 옵션 B
```

**예상 출력:** 8개 서브커맨드(`review`, `commit`, `pr`, `refactor`, `analyze`, `ask`, `skills`, `run`)가 한국어 설명과 함께 표시됩니다.

---

## 4단계 — 첫 명령 실행 (모델 자동 다운로드)

가장 간단한 자유 질의로 gemma-cli·MLX·gemma4 모두가 잘 연결되었는지 확인합니다. **처음 실행하는 모델은 HuggingFace에서 자동으로 다운로드**되므로 첫 응답까지는 다운로드 시간만큼 더 걸립니다(이후엔 캐시되어 빠릅니다).

```bash
gemma ask "Python에서 list와 tuple의 차이를 한 줄로 알려줘."
```

스트리밍으로 한국어 답이 흘러나오고 마지막에 `(세션 ID: ...)`가 표시되면 **전체 파이프라인 OK**.

> 미리 모델을 받아두려면(선택): `uv run huggingface-cli download mlx-community/gemma-3n-E4B-it-lm-4bit`
> 다운로드된 모델은 `~/.cache/huggingface/`에 캐시됩니다.

---

## 5단계 — 권장 설정 파일 만들기 (선택)

코드 기본값은 가벼운 `mlx-community/gemma-3n-E4B-it-lm-4bit`입니다. `refactor`·`review` 같은 코드 작업은 더 큰 모델(`mlx-community/gemma-3-text-27b-it-4bit`)이 diff 정확도와 분석 깊이가 확연히 좋습니다. 명령어별로 골라 쓰도록 설정해두세요.

```bash
mkdir -p ~/.config/gemma-cli
cat > ~/.config/gemma-cli/config.yaml <<'YAML'
# MLX 모델 경로(HuggingFace 저장소 이름 또는 로컬 MLX 디렉터리)
model: mlx-community/gemma-3-text-27b-it-4bit   # 무거운 기본(약 15GB) — 코드 작업용
temperature: 0.2
max_tokens: 2048

# 명령어별 오버라이드
commands:
  ask:
    model: mlx-community/gemma-3n-E4B-it-lm-4bit   # 자유 질의는 가벼운 e4b 로 빠르게
YAML
```

> 32GB 미만 메모리라면 27b가 버거울 수 있습니다. 모든 명령을 가볍게 쓰려면 `model:`을 `mlx-community/gemma-3n-E4B-it-lm-4bit`로 두세요.

### 확인

```bash
cat ~/.config/gemma-cli/config.yaml
gemma ask "한 줄로 자기소개 해줘." 2>&1 | head -5
```

---

## 6단계 — `commit`·`pr` 스킬을 어디서나 쓸 수 있게 (선택)

`gemma /commit`, `gemma /pr` 같은 슬래시 커맨드는 **사용자 스킬 디렉터리(`~/.config/gemma-cli/skills/`)** 에 스킬이 있어야 어느 git 저장소에서도 동작합니다. 프로젝트의 `.gemma/skills/` 두 파일을 글로벌로 복사:

```bash
mkdir -p ~/.config/gemma-cli/skills
cp .gemma/skills/commit.md ~/.config/gemma-cli/skills/commit.md
cp .gemma/skills/pr.md     ~/.config/gemma-cli/skills/pr.md
```

### 확인

```bash
gemma skills
```

`commit`, `pr` 행이 표 안에 나오면 OK.

이제 다른 프로젝트에서 다음과 같이 쓸 수 있습니다:

```bash
cd ~/some-other-repo
git add .
gemma /commit       # 메시지 자동 생성 → 승인 → 커밋
```

---

## 7단계 — 동작 시나리오 한 바퀴 돌려보기

빠른 손풀이로 모든 명령어가 잘 도는지 확인합니다.

```bash
# 임시 git 저장소 생성
mkdir -p /tmp/gemma-tour && cd /tmp/gemma-tour
git init -q -b main
git config user.email me@example.com
git config user.name me
echo "def add(a, b): return a + b" > calc.py
git add calc.py && git commit -q -m "init"

# 1) 자유 질의
gemma ask "Python에서 deepcopy와 copy의 차이는?"

# 2) 파일 리뷰
gemma review calc.py

# 3) 새 함수 추가 후 스테이징
echo "def multiply(a,b): return a*b" >> calc.py
git add calc.py

# 4) 슬래시 커맨드로 커밋
gemma /commit

# 5) 디렉터리 분석
gemma analyze .

# 6) 리팩토링 제안 (적용은 거절해도 OK)
gemma refactor calc.py -i "타입 힌트를 추가해줘"
```

여기까지 멈춤 없이 진행되면 **모든 기능 정상**.

---

## 흔한 문제 해결

### Q. `gemma: command not found`

옵션 A(글로벌 설치)로 깔지 않았거나, PATH가 안 잡혔습니다.

```bash
ls ~/.local/bin/gemma           # 없으면: uv tool install . 다시
echo $PATH | tr ':' '\n' | grep '.local/bin'   # 비어 있으면 PATH 추가 필요
```

해결:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Q. `mlx-lm 패키지가 설치되어 있지 않습니다`

`mlx-lm`은 Apple Silicon 전용 의존성입니다. 설치를 다시 진행하세요.

```bash
uname -m                 # arm64 인지 확인 (x86_64면 동작 불가)
uv pip install mlx-lm    # 또는 uv sync --extra dev
```

### Q. `MLX 모델을 로드할 수 없습니다`

`config.yaml`의 `model:` 값이 올바른 MLX 모델 경로(HuggingFace 저장소 이름 또는 로컬 디렉터리)인지 확인하세요. 첫 실행은 다운로드로 시간이 걸릴 수 있습니다.

```bash
# 모델을 미리 받아 캐시 상태 확인
uv run huggingface-cli download mlx-community/gemma-3n-E4B-it-lm-4bit
```

### Q. 응답이 매우 느리거나 메모리가 부족합니다

`mlx-community/gemma-3-text-27b-it-4bit`는 무겁습니다(약 15GB, 메모리 32GB+ 권장). 메모리가 부족하면 macOS 활성 상태 보기에서 "스왑 사용"이 치솟습니다. 더 가벼운 모델로 바꾸세요:

```bash
# config.yaml의 model: 을 e4b로 변경
#   model: mlx-community/gemma-3n-E4B-it-lm-4bit
# 또는 더 작은
#   model: mlx-community/gemma-3n-E2B-it-4bit
```

### Q. `gemma /commit` 에서 메시지가 이상하게 짧거나 형식이 깨집니다

작은 모델이 복잡한 프롬프트를 따라가지 못해서 그렇습니다. `config.yaml`에 `commands.run.model: mlx-community/gemma-3-text-27b-it-4bit` 오버라이드를 권장.

### Q. `gemma pr` 이 실행되지만 PR이 안 만들어집니다

GitHub `gh` CLI 미설치 시 본문만 출력하고 종료합니다. 설치:

```bash
brew install gh
gh auth login
```

### Q. `gemma refactor` → `error: corrupt patch at line N`

작은 모델이 만든 diff 형식이 깨졌습니다. 원본 파일은 그대로 보존됩니다. `config.yaml`에 `commands.refactor.model: mlx-community/gemma-3-text-27b-it-4bit` 오버라이드를 권장.

### Q. 응답이 영어로 나옵니다

설정 디렉터리에 `GEMMA.md`를 두면 모든 응답에 추가 지침을 줄 수 있습니다:

```bash
cat > ~/.config/gemma-cli/GEMMA.md <<'EOF'
모든 답변은 반드시 한국어로 작성한다.
코드 예시에도 한국어 주석을 단다.
EOF
```

> ※ `GEMMA.md`는 현재 작업 디렉터리 → 상위 → … 순으로 탐색됩니다. 홈 디렉터리에도 두면 어디서나 적용됩니다.

---

## 다음 단계

- 명령어별 상세 옵션은 [README.md](../README.md) 의 §4 참고
- 자신만의 스킬을 만들고 싶다면 [README.md §6 — 사용자 정의 스킬](../README.md#6-사용자-정의-스킬)
- 프로젝트별 답변 규칙을 강제하고 싶다면 [README.md §5 — `GEMMA.md`](../README.md#5-프로젝트-지침-gemmamd)
- 전체 아키텍처는 [`architecture.svg`](architecture.svg), 자동화 흐름은 [`command-flow.svg`](command-flow.svg)

문제가 해결되지 않는다면 `gemma --help` 출력과 `~/.config/gemma-cli/config.yaml` 내용을 함께 공유하면 진단이 빠릅니다.
