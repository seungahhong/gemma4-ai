# 시작하기 — gemma-cli 환경 구축 가이드

이 문서는 **빈 macOS 또는 Linux 환경에서 gemma-cli를 처음 설치하고 첫 명령을 성공적으로 실행할 때까지**의 모든 단계를 안내합니다. 명령어는 그대로 복사·붙여넣어 실행할 수 있으며, 각 단계마다 정상 동작을 확인하는 방법을 함께 적었습니다.

소요 시간: 모델 다운로드 시간(약 10분)을 포함해 **20~30분**.

---

## 사전 점검 — 내 환경에서 시작해도 되나?

| 항목 | 요구 | 확인 명령 |
|------|------|-----------|
| OS | macOS 12+ / Ubuntu 22.04+ | `uname -a` |
| 디스크 여유 | 10GB 이상 (모델 + 도구) | `df -h ~` |
| RAM | 8GB 이상(e4b) / 32GB 이상(26b) | macOS: `system_profiler SPHardwareDataType \| grep Memory` |
| 인터넷 | 모델 다운로드용 (이후엔 오프라인 가능) | `curl -sI https://ollama.com \| head -1` |

기준에 못 미치면 더 가벼운 모델(`gemma4:e2b`)을 쓰거나 클라우드 인스턴스를 권장합니다.

---

## 1단계 — Python 3.11 이상 확인

```bash
python3 --version
```

**예상 출력:** `Python 3.11.x` ~ `Python 3.14.x`

### 버전이 낮거나 없다면

- **macOS:** `brew install python@3.12` (먼저 [Homebrew](https://brew.sh) 설치 필요)
- **Ubuntu:** `sudo apt-get update && sudo apt-get install -y python3.12 python3.12-venv`

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

## 3단계 — ollama 설치

ollama는 로컬에서 LLM을 돌리는 서버입니다.

### macOS

```bash
brew install ollama
```

또는 [ollama.com/download](https://ollama.com/download) 의 .dmg 설치.

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 확인

```bash
ollama --version
```

**예상 출력:** `Warning: could not connect to a running Ollama instance` + `client version is 0.x.x`

서버가 아직 안 떠 있어 경고가 나오는 게 정상입니다. 다음 단계에서 띄웁니다.

---

## 4단계 — ollama 서버 시작

새 터미널을 하나 더 열고 거기서 실행하세요. (이 터미널은 사용 동안 켜둬야 합니다.)

```bash
ollama serve
```

기존 터미널로 돌아와 확인:

```bash
curl -s http://localhost:11434/api/version
```

**예상 출력:** `{"version":"0.x.x"}`

> **macOS GUI 앱으로 설치했다면?** 메뉴바에 ollama 아이콘이 있으면 이미 서버가 실행 중입니다. 따로 `ollama serve` 실행 불필요.

---

## 5단계 — gemma4 모델 받기

기본 모델(약 9.6GB) 다운로드:

```bash
ollama pull gemma4:e4b
```

> 시간이 좀 걸립니다(보통 5~10분). 진행 막대가 표시됩니다.

리뷰·리팩토링 품질을 더 높이고 싶으면 큰 모델도 받아두세요(17GB, RAM 32GB+ 권장):

```bash
ollama pull gemma4:26b
```

### 확인

```bash
ollama list
```

**예상 출력:**
```
NAME          ID              SIZE      MODIFIED
gemma4:e4b    c6eb396dbd59    9.6 GB    2 minutes ago
```

### 동작 확인 (모델이 제대로 깔렸는지)

```bash
ollama run gemma4:e4b "안녕? 한 줄로 답해줘."
```

한국어 응답이 한 줄 나오면 모델 OK. `/bye` 또는 `Ctrl+D`로 빠져나오세요.

---

## 6단계 — gemma-cli 설치

프로젝트 디렉터리로 이동:

```bash
cd /Users/seungah.hong/workspace/gemma4-ai
```

> 자신의 경로에 맞게 바꿔주세요. git clone부터 한다면 `git clone <URL> gemma4-ai && cd gemma4-ai`.

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

## 7단계 — 첫 명령 실행

가장 간단한 자유 질의로 ollama·gemma-cli·gemma4 모두가 잘 연결되었는지 확인합니다:

```bash
gemma ask "Python에서 list와 tuple의 차이를 한 줄로 알려줘."
```

스트리밍으로 한국어 답이 흘러나오고 마지막에 `(세션 ID: ...)`가 표시되면 **전체 파이프라인 OK**.

> 응답이 안 나오고 멈춰 있다면? 다른 터미널에서 `ollama serve` 가 살아 있는지 확인 (`curl -s http://localhost:11434/api/version`).

---

## 8단계 — 권장 설정 파일 만들기 (선택)

`refactor`와 `review`는 e4b로도 동작하지만, diff 정확도와 분석 깊이는 `26b`가 확연히 좋습니다. 두 모델을 다 받았다면 명령어별로 골라 쓰도록 설정해두세요.

```bash
mkdir -p ~/.config/gemma-cli
cat > ~/.config/gemma-cli/config.yaml <<'YAML'
model: gemma4:e4b
host: http://localhost:11434
temperature: 0.2

# 명령어별 오버라이드
commands:
  refactor:
    model: gemma4:26b
  review:
    model: gemma4:26b
  run:
    model: gemma4:26b
YAML
```

### 확인

```bash
cat ~/.config/gemma-cli/config.yaml
gemma ask "어느 모델이 답하는 중이야?" 2>&1 | head -5
```

---

## 9단계 — `commit`·`pr` 스킬을 어디서나 쓸 수 있게 (선택)

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

## 10단계 — 동작 시나리오 한 바퀴 돌려보기

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

### Q. `ollama 서버에 연결할 수 없습니다`

다른 터미널의 `ollama serve`가 죽었거나, 다른 포트를 쓰고 있습니다.

```bash
# 살아 있는지 확인
curl -sI http://localhost:11434/api/version

# 죽었으면 새 터미널에서 다시
ollama serve

# 포트가 점유되어 있다면 (다른 ollama 인스턴스가 있는지 확인)
lsof -iTCP:11434 -sTCP:LISTEN
```

### Q. `model 'gemma4:e4b' not found`

모델이 안 받혀 있습니다.

```bash
ollama pull gemma4:e4b
```

### Q. 응답이 매우 느립니다

`gemma4:26b`는 무겁습니다. RAM 부족이면 macOS 활성 상태 보기에서 "스왑 사용" 수치가 치솟습니다. 두 가지 해결:

```bash
# 가벼운 모델로 임시 전환
gemma ask --help    # (e4b가 기본)

# 또는 설정에서 26b 오버라이드 제거
```

### Q. `gemma /commit` 에서 메시지가 이상하게 짧거나 형식이 깨집니다

작은 모델(e4b)이 복잡한 프롬프트를 따라가지 못해서 그렇습니다. 8단계의 `commands.run.model: gemma4:26b` 오버라이드를 권장.

### Q. `gemma pr` 이 실행되지만 PR이 안 만들어집니다

GitHub `gh` CLI 미설치 시 본문만 출력하고 종료합니다. 설치:

```bash
brew install gh
gh auth login
```

### Q. `gemma refactor` → `error: corrupt patch at line N`

작은 모델이 만든 diff 형식이 깨졌습니다. 원본 파일은 그대로 보존됩니다. 8단계의 `commands.refactor.model: gemma4:26b` 오버라이드를 권장.

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
