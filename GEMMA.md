# gemma-cli 프로젝트 지침

이 파일은 gemma-cli가 모든 명령 실행 시 자동으로 시스템 프롬프트에 덧붙이는 프로젝트 지침이다.

## 응답 규칙
- 모든 답변은 한국어로 작성한다.
- 코드 예시에는 한국어 주석을 포함한다.
- 외부 라이브러리를 제안할 때는 라이선스 종류를 함께 명시한다.

## 프로젝트 컨텍스트
- 본 프로젝트는 Python 3.11+ CLI이며 `click`, `httpx`, `rich`, `pydantic`, `pyyaml`을 사용한다.
- 모든 ollama 호출은 단위 테스트에서 `respx`로 모킹한다.
- 새 명령어는 `src/gemma_cli/commands/`, 공통 모듈은 `src/gemma_cli/services/`에 둔다.
