# 🧠 P-Reinforce Wiki
> **자율 지식화 에이전트** — Karpathy 영속적 위키 × RL 분류 정책

[![P-Reinforce](https://img.shields.io/badge/Engine-P--Reinforce_v1.0-blueviolet)](.)
[![GitHub Actions](https://img.shields.io/badge/Auto_Sync-GitHub_Actions-2ea44f)](https://github.com/a01034492969-pixel/forha-wiki/actions)

---

## 🚀 빠른 시작

```powershell
# 1. 새 Raw 노트 생성
.\reinforce.ps1 new "오늘 배운 것" "강화학습은 보상 함수를 최대화하는 정책을 학습한다"

# 2. 위키로 변환 (분류 + 문서화 + GitHub 커밋)
.\reinforce.ps1 add "00_Raw\2026-07-25\오늘 배운 것.md"

# 3. 또는 전체 스캔
.\reinforce.ps1 scan

# 4. 현황 확인
.\reinforce.ps1 status
```

## 📂 구조

| 폴더 | 역할 |
|---|---|
| `00_Raw/` | 날짜별 원본 입력 (보존) |
| `10_Wiki/🛠️ Projects/` | 목표 중심 프로젝트 |
| `10_Wiki/💡 Topics/` | 개념·이론 지식 |
| `10_Wiki/⚖️ Decisions/` | 의사결정 기록 |
| `10_Wiki/🚀 Skills/` | 실행 패턴·프롬프트 |
| `20_Meta/` | 시스템 두뇌 (그래프, 정책, 목차) |
| `engine/` | Python RL 엔진 |

## 🤖 에이전트 피드백으로 가르치기

```powershell
# 칭찬 → 분류 가중치 강화
.\reinforce.ps1 praise "오늘 배운 것"

# 이동 → 경계 재설정
.\reinforce.ps1 move "오늘 배운 것" "Projects"
```

## ⚙️ 자동화

- **GitHub Actions**: `00_Raw/`에 파일 push 시 자동 변환
- **매일 자정**: 전체 스캔 크론 실행
- **Antigravity**: "위키에 추가해줘" 등 자연어 명령으로 호출 가능

---
*Powered by [P-Reinforce](engine/p_reinforce.py) + [Antigravity](.agents/skills/p-reinforce/SKILL.md)*
