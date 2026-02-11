## 유튜브 대본 초안 작성 자동화 툴

타겟 1개 + 참고 2개 대본을 입력하면, 구조 패턴을 추출하고 "브릿지+주제" 단위 목차/초안을 생성하는 파이프라인입니다.

OpenAI API 기반으로 설계되어 있으며, API 키 없이도 기본 흐름을 점검할 수 있도록 `offline_mode`를 지원합니다.

---

## 디렉터리 구조

```text
inputs/
  sample_input.json
pipeline/
  preprocess.py   # Step A 전처리(문단 분리/태그)
  analyze.py      # Step B 구조 분석(OpenAI 1차)
  outline.py      # Step C 혼합 목차 생성(OpenAI 2차)
  draft.py        # Step D 단락별 초안 생성(OpenAI 3차)
  validate.py     # 검증/가드레일(규칙 엔진 + 선택적 LLM Judge)
  runner.py       # 파이프라인 오케스트레이션
outputs/
  outline.md
  draft_sections.md
  report.json
src/
  main.py         # CLI 진입점
```

---

## 입력 스키마 (필수)

`inputs/*.json`에 아래 키를 포함해야 합니다.

- `script_target`
- `script_ref1`
- `script_ref2`
- `title`
- `thumbnail_text`
- `viewer_persona`
- `creator_persona`
- `style_rules` (선택)
- `settings` (선택)

`settings` 주요 옵션:

- `offline_mode` (bool): true면 OpenAI 호출 없이 규칙 기반 목업 실행
- `strict_fact_mode` (bool): 입력 밖 숫자/고유명사/지명 후보 플래그
- `section_count` (int): 생성 섹션 개수
- `min_section_chars`, `max_section_chars` (int): 섹션 길이 범위
- `enable_llm_judge` (bool): 저비용 LLM 검수 리포트 활성화

---

## 실행 방법

### 1) 오프라인 테스트 실행

```bash
python src/main.py --input inputs/sample_input.json --output outputs
```

### 2) OpenAI API 모드 실행

1. `inputs/sample_input.json`에서 `"offline_mode": false`로 변경
2. 환경 변수 설정

```bash
export OPENAI_API_KEY="your_api_key"
```

3. 실행

```bash
python src/main.py --input inputs/sample_input.json --output outputs
```

---

## 출력 파일

- `outputs/outline.md`
  - 브릿지+주제 목차
  - 섹션별 목적/감정/댓글 유도 포인트
- `outputs/draft_sections.md`
  - 단락별 초안 (브릿지 / 주제 분리)
- `outputs/report.json`
  - 규칙 위반 리포트(포맷/말투/길이/팩트 확장 플래그 등)

추가 디버그 산출물:

- `outputs/analysis.json`
- `outputs/preprocess.json`

---

## 검증 로직 요약

`pipeline/validate.py`에서 기본적으로 아래를 검사합니다.

1. 브릿지+주제 포맷 완성 여부
2. `~니다 종결` 비율(룰 포함 시)
3. 어색한 종결 패턴(`~을.`, `~줄은.` 등)
4. 섹션 길이 범위
5. strict fact mode의 입력 밖 후보(숫자/영문 고유명사/지명·인명 패턴)

`enable_llm_judge=true`일 경우, 별도 LLM 호출로 "수정 없는 위반 리포트"를 추가로 기록합니다.