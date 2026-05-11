# MindBuddhi (붓다지혜마음케어)

AI 붓다 지혜 상담 서비스 - 팔만대장경의 지혜를 현대적인 감각으로 전달합니다.

## 🌟 프로젝트 소개
**MindBuddhi**는 팔만대장경(중아함경 등)의 방대한 지혜를 기반으로 사용자에게 따뜻한 위로와 명확한 통찰을 제공하는 AI 상담 서비스입니다. 단순한 챗봇을 넘어, 성현의 가르침과 사주, MBTI 등을 결합하여 다각도에서 마음을 돌봅니다.

## ✨ 주요 기능
- **고민 상담**: 팔만대장경의 가르침을 바탕으로 현대인의 고민에 대한 지혜로운 답변 제공
- **경전 질문**: 불교 경전에 대한 깊이 있는 질문과 답변 (RAG 기술 활용)
- **사주 및 별자리**: 사주 명리와 별자리를 불교적 관점에서 해석해주는 영적 가이드
- **MBTI 성격 상담**: 사용자의 성향에 맞춘 맞춤형 위로와 조언
- **음성 지원 (TTS)**: 고품질 음성 클로닝 기술을 통한 따뜻하고 부드러운 목소리 지원

## 🏗️ 프로젝트 구조
- `service/`: 메인 상담 서비스의 백엔드(FastAPI) 및 프론트엔드 코드
- `mindbuddi_clean_export/`: 배포 및 관리를 위해 최적화된 클린 버전
- `service/frontend/`: 사용자 인터페이스 (HTML/JS/CSS)

## 🚀 시작하기

### 환경 설정
1. `.env` 파일을 생성하고 다음 정보를 입력합니다:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_key
   OPENAI_API_KEY=your_openai_key
   ```

### 서버 실행
메인 서비스를 실행하려면:
```bash
python service/main.py
```
(기본 포트: 8000)

클린 버전을 실행하려면:
```bash
python mindbuddi_clean_export/main.py
```
(기본 포트: 8001)

## 🎨 로고 및 브랜딩
본 프로젝트는 **MindBuddhi**라는 브랜드명과 연꽃을 형상화한 로봇 붓다 로고를 사용합니다.

---
© 2026 MindBuddhi Team. Powered by DeepFountain & IMDS.
