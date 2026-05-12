# MindBuddhi (붓다지혜마음케어)

![Banner](docs/images/banner.png)

## 🕊️ 당신의 마음을 돌보는 지혜의 동반자
**MindBuddhi**는 팔만대장경의 방대한 지혜와 현대의 AI 기술을 결합하여, 일상의 고민에 대한 깊이 있는 통찰과 따뜻한 위로를 전하는 **불교 기반 감성 지능 상담 서비스**입니다.

---

## ✨ 주요 기능

![Features](docs/images/features.png)

### 💬 지혜로운 고민 상담 (MindBuddhi Chat)
현대인의 스트레스, 관계, 자아 성찰 등 다양한 고민에 대해 붓다의 가르침을 바탕으로 맞춤형 조언을 제공합니다. 단순히 정보를 전달하는 것이 아니라, 당신의 마음을 깊이 공감하고 위로합니다.

### 📜 팔만대장경 지혜 탐색 (Scripture Insights)
방대한 불교 경전 속에서 당신에게 지금 꼭 필요한 구절을 찾아냅니다. 최신 AI 기술을 통해 경전의 원문과 현대적 해석을 동시에 제공하여 삶의 복잡한 질문들에 대한 명확한 해답을 제시합니다.

### 🌌 영적 가이드 (Zodiac & Saju)
동양의 전통 지혜인 사주 명리와 별자리 해석을 불교적 통찰과 연결합니다. 당신의 타고난 성향을 이해하고, 조화로운 삶을 살 수 있는 방향을 제시하는 영적 길잡이가 되어드립니다.

### 🎙️ 따뜻한 음성 교감 (Voice Healing)
고품질 음성 클로닝 기술을 통해 구현된 부드럽고 인자한 목소리로 상담을 진행할 수 있습니다. 텍스트를 넘어 목소리로 전달되는 따뜻한 울림을 통해 진정한 마음의 평온을 경험해보세요.

---

## 🛠️ 기술적 가이드 (Technical Overview)
이 프로젝트는 최신 AI 기술 스택을 활용하여 안정적이고 지능적인 서비스를 제공합니다.

- **Backend**: FastAPI (Python)를 활용한 고성능 비동기 API 서버
- **AI Core**: OpenAI GPT-4o 기반의 맞춤형 상담 로직
- **Knowledge Base**: Supabase Vector Store를 통한 팔만대장경 RAG 구현
- **Voice Engine**: 감성적인 고품질 TTS 라이브러리 활용

---

<details>
<summary><b>🚀 개발자 설정 및 실행 방법 (Developer Guide)</b></summary>

### 1. 환경 설정
`.env` 파일에 필요한 API 키 및 데이터베이스 정보를 설정합니다.
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`

### 2. 서버 실행
- **메인 상담 서비스**: `python service/main.py` (Port: 8000)
- **배포용 클린 버전**: `python mindbuddi_clean_export/main.py` (Port: 8001)

</details>

---
© 2026 MindBuddhi Team. All rights reserved.
