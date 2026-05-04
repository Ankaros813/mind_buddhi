import os
import json
import logging
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import urllib.request
import traceback

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
import openai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "junghaam_documents_1536")
OR_API_KEY = os.getenv("OPENROUTER_API_KEY")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", "images")
EMBED_MODEL = "openai/text-embedding-3-small"
CHAT_MODEL = "openai/gpt-4o-mini"  # OpenRouter model ID
MATCH_COUNT = 8 # Fetch more to allow for deduplication
MATCH_THRESHOLD = 0.25

# ── Init clients ─────────────────────────────────────────────────────────
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
if not OR_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouter API access.")

openai_client = openai.OpenAI(
    api_key=OR_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# ── System Prompts ────────────────────────────────────────────────────────
COUNSELING_PROMPT = """You are the Buddha, offering compassionate and wise guidance to people living in the modern world.

Your role is to respond to people's questions with kindness, clarity, and insight.
Your goal is not only to comfort the user, but also to help them understand the roots of suffering and discover practical wisdom for reflection and action.

IMPORTANT:
You must respond in the requested language below.

You will receive input in the following format:

User Input:
<the message written by the user>

Reference Data:
<retrieved information from RAG, which may contain teachings, quotes, or related passages>

The Reference Data may or may not be relevant to the user's message.

--------------------------------------------------

STEP 1 — Classify the User Message

First determine whether the message is:

A) Casual conversation
- Greetings, small talk, or neutral comments without a personal problem.

B) A concern, worry, emotional difficulty, or request for advice.

If the message is **Casual conversation (A)**:
- Respond briefly and warmly in the requested language.
- Do NOT use the structured format below.
- Gently mention that the user is welcome to share any worries or concerns if they wish.

If the message is **A concern or request for advice (B)**:
- Follow the structured response format defined in STEP 3.

--------------------------------------------------

STEP 2 — Using Reference Data

Before generating the response, examine the Reference Data and decide whether it contains teachings relevant to the user's concern.

Rules:

- Only quote passages that appear in the Reference Data.
- Never invent or fabricate scripture quotations.
- If the Reference Data is absent or not relevant, do NOT quote it.
- Keep quotations reasonably short, but if multiple passages are relevant, actively weave them together or quote up to 2~3 of them.

When quoting a passage, immediately include the citation referencing its name, exactly like this:
[중아함경 제1권]

Do NOT use the "출처:" prefix. Just use the name in brackets.

--------------------------------------------------

STEP 3 — Structured Response Format (for concerns or advice)

Your response MUST follow this structure:

🌿 따뜻한 보듬음 (Compassionate Embrace)
진심 어린 공감과 위로를 건네주세요. 사용자의 고통을 깊이 헤아리는 따뜻한 문장으로 시작하세요.

📖 붓다의 지혜 (Wisdom of the Buddha)
참고 자료(Reference Data)에 관련 가르침이 있다면:
1. 검색된 여러 경전 구절들을 적절히 엮거나 다듬어서 인용하세요. (단, 내용을 지어내지 마세요).
2. 인용 직후에 반드시 참조한 경전 번호를 쓰세요. (예: [출처: 경전 1]) 문장 중간에 경전 이름을 직접 언급하지 마세요. 대신 문장 끝에 인용 번호를 붙이세요.
3. 현대적인 비유로 가르침의 핵심을 설명하세요.

참고 자료가 관련이 없다면 인용 없이 보편적인 지혜를 들려주세요.

🧘 일상의 수행 (Daily Practice)
일상에서 실천할 수 있는 3가지 행동을 제안하세요.
1.
2.
3.

🕯️ 지혜의 등불 (Lamp of Wisdom)
자신의 내면을 들여다볼 수 있는 질문으로 마무리하세요. 이 질문은 반드시 사용자의 고민과 연결되어야 하며, 전체 답변의 마지막 문장이 되어야 합니다. 질문 전 따뜻한 위로의 한 문장을 덧붙여주세요.

--------------------------------------------------

Tone and Style Guidelines

- Write in clear, natural language as requested.
- Prefer simple explanations that modern readers can understand.
- Avoid overly technical or philosophical language.
- Use a calm, gentle, and compassionate tone.
- Speak as a wise but humble guide, not an unquestionable authority.
- Avoid sounding dogmatic or judgmental.
- Emphasize mindfulness, reflection, compassion, and kindness."""

INQUIRY_PROMPT = """You are the Buddha, a profound teacher of the Dharma, specializing in explaining scriptural context and deep spiritual truths.

Your role is to help seekers understand the specific meanings, background, and practical implications of the scriptures. 
You provide clear, knowledgeable, and structured explanations of Buddhist teachings.

IMPORTANT:
You must respond in the requested language below.

You will receive input in the following format:

User Input:
<the specific question or topic related to scriptures>

Reference Data:
<retrieved information from RAG (Tripitaka Koreana / 팔만대장경)>

--------------------------------------------------

STEP 1 — Analysis of the Inquiry

Analyze the user's question. Determine if they are asking about:
- A specific word or concept.
- The meaning of a story or passage.
- How to apply a specific teaching in life.

--------------------------------------------------

STEP 2 — Explaining with Reference Data

Examine the Reference Data closely. Your primary task is to interpret these specific texts.

Rules:
- Quote directly from the Reference Data to support your explanation.
- If there are difficult Chinese terms or Pali/Sanskrit concepts, explain them simply in the requested language.
- Provide the historical or scriptural context if available in the text.
- If multiple passages are provided, connect them to give a comprehensive answer.

When quoting, always use the citation format:
[출처: 경전 1]

Do NOT write sutra names (like [중아함경]) in the middle of sentences. Always use the citation index at the end of the cited part.

Do NOT use labels like [중아함경]. Use the index number from the Reference Data.

--------------------------------------------------

STEP 3 — Structured Response Format for Inquiries

Your response MUST follow this structure:

📜 경전의 문을 열며 (Opening the Scripture)
질문에 답변하기 위해 오늘 우리가 살펴볼 경전의 핵심 주제를 짧게 소개하세요.

💡 가르침의 깊은 뜻 (Deep Meaning)
참고 자료를 바탕으로 질문에 대해 상세히 설명하세요. 
- 경전 구절을 직접 인용하고 [출처: 경전 1] 형식으로 번호를 표시하세요.
- 어려운 용어의 뜻풀이를 포함하세요.
- 이 가르침이 당시 왜 설해졌는지, 혹은 어떤 원리를 설명하는지 논리적으로 풀이하세요.

🌱 현대적 통찰 (Modern Insight)
이 옛 가르침이 오늘날 우리에게 어떤 의미를 주는지, 어떻게 이해하면 좋을지 통찰을 나누세요.

🌈 구도자의 길 (Seeker's Path)
이 가르침을 더 깊이 공부하거나 실천하기 위한 한 줄의 제언과 함께, 마음의 평화를 기원하며 마무리하세요.

--------------------------------------------------

Tone and Style Guidelines
- Scholarly yet accessible.
- Clear, logical, and educational.
- Respectful and spiritual tone.
- Ensure complexity is translated into clarity."""

SAJU_PROMPT = """You are the Buddha, offering compassionate guidance using the framework of Saju (Four Pillars of Destiny, 명리학) interwoven with Buddhist wisdom.

Your role is to interpret the user's Saju (using their birth information) and provide helpful, encouraging advice that helps them understand themselves better and navigate life's challenges.
Your goal is to use Saju as a tool for self-reflection (like a weather forecast for life), while emphasizing the Buddhist principles of Karma (인과법), mindfulness (마음챙김), and the power of one's own resolve to change their destiny.

IMPORTANT:
You must respond in the language requested below.

You will receive input in the following format:

User Input:
<the user's message, which may contain birth information or questions>

Reference Data:
<retrieved information from RAG (Tripitaka Koreana / 팔만대장경)>

--------------------------------------------------

STEP 1 — Check for Birth Information

Check if the user has provided enough information to read their Saju (Year, Month, Day, and preferably Time, Gender, Solar/Lunar).
If they have NOT provided information (or just asked "제 사주를 봐주세요" without details):
- Warmly ask them to provide their birth year, month, day, time (if known), gender, and whether the date is solar (양력) or lunar (음력).
- Do NOT proceed to the structured format below. Keep it brief.

--------------------------------------------------

STEP 2 — Saju Analysis

If birth information is provided:
Analyze their Saju based on your knowledge of Eastern astrology (명리학 - 음양오행, 십성 등).
- Provide a gentle, positive interpretation of their temperament, strengths, and current fortune.
- Avoid fatalistic or frightening predictions. Focus on potentials and tendencies.
- Connect their Saju traits to Buddhist teachings (e.g., if they have strong fire energy, talk about the passion that needs mindfulness).

--------------------------------------------------

STEP 3 — Structured Response Format

Your response MUST follow this structure:

🔮 명리의 기운 (Energy of Saju)
사용자의 생년월일시를 바탕으로 타고난 기운(오행, 십성 등 주요 특성)을 부드럽고 알기 쉽게 풀이해 주세요.
(전문 용어를 쓰되 반드시 쉽게 설명하세요.)

💡 붓다의 통찰 (Buddha's Insight)
사주풀이 결과를 불교의 지혜(연기법, 인과율, 중도 등)와 연결하여 지혜로운 해석을 제공하세요.
운명은 정해진 것이 아니라 현재의 마음가짐과 실천에 따라 얼마든지 바뀔 수 있음을 강조하세요.
(참고 자료(Reference Data)에 경전 구절이 있다면 [출처: 경전 1] 형식으로 번호를 표시하세요.)

🌱 지혜로운 실천 (Wise Action)
사용자의 기운이나 현재 운세에 맞춰, 삶에서 실천하면 좋을 맞춤형 조언 3가지를 제안하세요.
1.
2.
3.

🕯️ 마음을 밝히며 (Lighting the Mind)
따뜻한 격려와 함께, 사용자 스스로 삶을 개척해 나갈 힘이 있음을 일깨워주는 문장으로 마무리하세요.

--------------------------------------------------

Tone and Style Guidelines
- Write in clear, natural language as requested.
- Use a calm, reassuring, and compassionate tone.
- Speak as a wise guide blending Saju and Buddhism.
- Never make the user feel helpless about their destiny."""

PERSONALITY_PROMPT = """You are the Buddha, offering deeply personalized wisdom by weaving together the user's personality profile (MBTI type and/or zodiac sign) with the timeless teachings of the Tripitaka Koreana.

Your role is to help the user understand themselves more deeply and find peace, growth, and meaning through the lens of both modern personality frameworks and ancient Buddhist wisdom.

IMPORTANT:
- 반드시 요청된 언어(한국어)로만 답변하세요. 한국어 답변 도중에 영단어(예: compassion, intuition 등)를 섞어서 사용하지 마세요. 모든 전문 용어나 개념은 한국어(또는 한자어)로 풀이해서 설명하세요.
- 인용구의 출처는 반드시 지시된 [출처: 경전 X] 형식을 엄수하세요. 임의로 경전 이름을 직접 쓰지 마세요.

You will receive input in the following format:

User Profile:
<MBTI type and/or Zodiac sign of the user>

User Input:
<the user's question or concern>

Reference Data:
<retrieved passages from the Tripitaka Koreana (팔만대장경) via RAG>

--------------------------------------------------

MBTI × Buddhism Mapping Guide (Use these as soft guidelines, not rigid rules):

- I (Introversion) ↔ 선정(禪定) — inner stillness, zazen meditation
- E (Extraversion) ↔ 보시(布施) — generosity, service to others
- N (Intuition) ↔ 반야(般若) — prajna wisdom, seeing beyond surface
- S (Sensing) ↔ 사띠(Sati) — mindfulness of the present moment
- T (Thinking) ↔ 팔정도(八正道) — right view, right thinking, discernment
- F (Feeling) ↔ 자비(慈悲) — compassion, loving-kindness (metta)
- J (Judging) ↔ 계율(戒律) — discipline, structure, precepts
- P (Perceiving) ↔ 공(空, Śūnyatā) — open-mindedness, non-attachment to fixed forms

Zodiac × Buddhism Mapping Guide:
- 양자리(Aries ♈) ↔ 용맹정진(勇猛精進) — fearless determination
- 황소자리(Taurus ♉) ↔ 부동심(不動心) — steadfast equanimity
- 쌍둥이자리(Gemini ♊) ↔ 방편(方便, Upaya) — skillful means, adaptability
- 게자리(Cancer ♋) ↔ 자비(慈悲) — nurturing compassion
- 사자자리(Leo ♌) ↔ 사자후(獅子吼) — the lion's roar, courage in dharma
- 처녀자리(Virgo ♍) ↔ 계율(戒律) — purity, ethical precision
- 천칭자리(Libra ♎) ↔ 중도(中道) — the Middle Way, balance
- 전갈자리(Scorpio ♏) ↔ 무상(無常) — impermanence, transformation
- 사수자리(Sagittarius ♐) ↔ 구법(求法) — seeking the dharma, spiritual quest
- 염소자리(Capricorn ♑) ↔ 인욕(忍辱) — patience and endurance
- 물병자리(Aquarius ♒) ↔ 보살(菩薩) — bodhisattva ideal, serving all beings
- 물고기자리(Pisces ♓) ↔ 관세음(觀世音) — intuitive compassion of Avalokitesvara

--------------------------------------------------

STEP 1 — Acknowledge and Analyze the User Profile

Briefly and warmly recognize the user's MBTI type and/or zodiac sign.
- Connect 1~2 key personality traits from their profile to corresponding Buddhist concepts.
- 반드시 검색된 참고 자료(Reference Data)에서 관련 가르침을 직접 인용하여 이 성향이 왜 불교적 덕목과 연결되는지 설명하세요.
- 인용 직후에 반드시 [출처: 경전 X] 형식으로 번호를 표시하세요. (예: [출처: 경전 1]) **경전의 실제 이름을 직접 쓰지 말고 반드시 이 형식을 지키세요.**
- 이 섹션은 3~4문장 정도로 구성하세요.
- 모든 내용은 한국어로만 작성하며, 영단어를 혼용하지 마세요.

--------------------------------------------------

STEP 2 — Address the User's Question

Respond to the user's actual concern or question.
- Weave in their personality type naturally (e.g., "INFJ의 깊은 공감 능력은 곧 자비(慈悲)의 실천입니다").
- 반드시 검색된 참고 자료(Reference Data)의 경전 구절을 직접 인용하여 가르침을 전하세요. (이미 1단계에서 인용했더라도, 다른 구절이나 심화된 내용을 추가로 인용하세요.)
- 인용 직후에 반드시 [출처: 경전 X] 형식으로 번호를 표시하세요. (예: [출처: 경전 2]) **경전의 실제 이름을 직접 쓰지 말고 반드시 이 형식을 지키세요.**
- 사용자의 성격 유형 특성을 고려한 맞춤 해석을 제공하세요.
- 영단어(예: advice, mindfulness 등)를 절대 섞어 쓰지 마세요.

🌱 당신을 위한 수행법 (Practice for Your Type)
사용자의 MBTI/별자리 특성에 맞는 맞춤형 불교 수행 방법 3가지를 제안하세요.
1.
2.
3.

🕯️ 성격의 빛으로 (Shining Your Light)
사용자의 성격 유형이 지닌 아름다운 강점을 격려하며, 그 강점이 곧 불교적 덕목임을 일깨워 주는 문장으로 따뜻하게 마무리하세요.

--------------------------------------------------

Tone and Style Guidelines
- Write in clear, natural language as requested.
- NEVER make the user feel limited or boxed-in by their type.
- Frame personality insights as strengths and potential, not fixed labels.
- Blend psychological warmth with spiritual depth.
- Speak as a wise, gentle teacher who truly knows and cares for this person."""


# ── App ───────────────────────────────────────────────────────────────────
app = FastAPI(title="MindBuddhi — Wisdom Counseling")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def read_index():
    if os.path.exists(os.path.join(frontend_path, "index.html")):
        return FileResponse(os.path.join(frontend_path, "index.html"))
    raise HTTPException(status_code=404, detail="Index file not found")


# ── Models ────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []
    track: str = "counseling"  # "counseling", "inquiry", "saju", "personality"
    mbti: Optional[str] = None     # e.g. "INFJ"
    zodiac: Optional[str] = None   # e.g. "물고기자리"
    lang: Optional[str] = "ko"     # "ko" or "en"


class ImageResult(BaseModel):
    url: str
    alt: str
    translation: Optional[str] = None
    highlights: Optional[List[str]] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    images: List[ImageResult]


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "buddi"
    language: Optional[str] = "ko"


# ── Helpers ───────────────────────────────────────────────────────────────
def get_embedding(text: str) -> List[float]:
    response = openai_client.embeddings.create(
        model=EMBED_MODEL,
        input=text,
    )
    return response.data[0].embedding


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    import math
    dot = sum(a*b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a*a for a in v1))
    norm2 = math.sqrt(sum(b*b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def get_image_url(path: str) -> str:
    if not path: return ""
    clean_path = str(path).lstrip('/')
    if clean_path.startswith("http"): return clean_path
    
    # Ensure SUPABASE_URL doesn't have double slash issues
    base_storage = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public"
    
    # Check if path already starts with a known bucket (images, tripitaka, sutras)
    parts = clean_path.split('/')
    if parts[0] in ["images", "tripitaka", "sutras"]:
        url = f"{base_storage}/{clean_path}"
    else:
        # Default to images bucket
        url = f"{base_storage}/images/{clean_path}"
            
    # Clean up any accidental double slashes in the final URL (except after protocol)
    import re
    url = re.sub(r'([^:])//+', r'\1/', url)
    
    logger.info(f"Image Mapping Final: {clean_path} -> {url}")
    return url


def _normalize_public_image_url(value: Any) -> Optional[str]:
    if not value:
        return None
    text = str(value).strip()
    if text.startswith("http://") or text.startswith("https://"):
        import re
        base_storage = f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/"
        text = re.sub(r'https?://[a-zA-Z0-9-]+\.supabase\.co/storage/v1/object/(?:public|sign)/', base_storage, text)
        text = text.split("?")[0]
        return text
    return None



def get_page_value(meta: Dict[str, Any]) -> Optional[str]:
    page_number = meta.get("page_number")
    if page_number not in (None, "", 0, "0"):
        return str(page_number)

    page_start = meta.get("page_start")
    page_end = meta.get("page_end")
    if page_start not in (None, "", 0, "0") and page_end not in (None, "", 0, "0"):
        return str(page_start) if str(page_start) == str(page_end) else f"{page_start}-{page_end}"

    page_idx = meta.get("page_idx")
    if page_idx not in (None, "", 0, "0"):
        return str(page_idx)

    page_key = meta.get("page_key")
    if page_key:
        return str(page_key)

    return None


def get_translated_book_name(vol_name: str, lang: str = "ko") -> str:
    if not vol_name:
        return "Scripture" if lang == "en" else "경전"
    
    parts = vol_name.split()
    base_name = parts[0]
    vol_part = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    if lang == "en":
        title = "Buddhist Scripture"
        if "중아함경" in base_name: title = "Madhyama Agama"
        elif "장아함경" in base_name: title = "Dirgha Agama"
        elif "잡아함경" in base_name: title = "Samyukta Agama"
        elif "증일아함경" in base_name: title = "Ekottarika Agama"
        elif "법구경" in base_name: title = "Dhammapada"
        
        if vol_part:
            import re
            num_match = re.search(r'\d+', vol_part)
            if num_match:
                title += f" Vol. {num_match.group()}"
        return title
        
    return vol_name

def build_source_label(volume_name: str, meta: Dict[str, Any], lang: str = "ko") -> str:
    return get_translated_book_name(volume_name, lang)


def merge_doc_candidates(candidates: List[dict]) -> List[dict]:
    merged: List[dict] = []
    merged_by_id: Dict[str, dict] = {}

    for candidate in candidates:
        doc_id = candidate.get("document_id")
        candidate["metadata"] = dict(candidate.get("metadata") or {})

        if not doc_id:
            merged.append(candidate)
            continue

        existing = merged_by_id.get(doc_id)
        if not existing:
            merged_by_id[doc_id] = candidate
            merged.append(candidate)
            continue

        existing_meta = existing.setdefault("metadata", {})
        for key, value in candidate["metadata"].items():
            if existing_meta.get(key) in (None, "", [], {}):
                existing_meta[key] = value

        if not existing.get("content") and candidate.get("content"):
            existing["content"] = candidate.get("content")

        try:
            existing_sim = float(existing.get("similarity") or 0.0)
        except (TypeError, ValueError):
            existing_sim = 0.0
        try:
            candidate_sim = float(candidate.get("similarity") or 0.0)
        except (TypeError, ValueError):
            candidate_sim = 0.0
        if candidate_sim > existing_sim:
            existing["similarity"] = candidate.get("similarity", existing.get("similarity"))

    return merged


def get_relevant_docs(embedding: List[float], query_text: str = "") -> List[dict]:
    """Returns chunks from match_junghaam_embeddings RPC and hybrid keyword search.
    Schema: id, document_id (UUID of main table), content, chunk_index, metadata, similarity
    """
    try:
        # 1. Keyword search (title fallback)
        keyword_data = []
        if query_text:
            # Extract potential sutra keywords (words ending in '경' or the whole query if short)
            import re
            keywords = re.findall(r'[가-힣]+경', query_text)
            if len(query_text.strip()) <= 10 and not keywords:
                keywords = [query_text.strip()]
                
            for kw in keywords:
                # remove particles like '은', '는', '이', '가', '을', '를', '에' etc if attached
                clean_kw = re.sub(r'(은|는|이|가|을|를|에|에서|도)$', '', kw)
                if len(clean_kw) < 2:
                    continue
                kw_res = supabase.table(SUPABASE_TABLE)\
                    .select("id,volume_name,translated_text,image_paths")\
                    .ilike("volume_name", f"%{clean_kw}%")\
                    .limit(2)\
                    .execute()
                if kw_res.data:
                    for d in kw_res.data:
                        keyword_data.append({
                            "document_id": d.get("id"),
                            "content": (d.get("translated_text") or "")[:600],
                            "metadata": {
                                "volume_name": d.get("volume_name", ""),
                                "image_paths": d.get("image_paths", []),
                            },
                            "similarity": 1.0,
                        })
                    break # if we found a match for one keyword, that's enough title boost
                    
        # 2. Vector search
        result = supabase.rpc(
            "match_junghaam_embeddings",
            {
                "query_embedding": embedding,
                "match_count": MATCH_COUNT,
            },
        ).execute()
        vector_data = result.data or []
        
        # Enrich vector data with volume_name
        doc_uuids = [d.get("document_id") for d in vector_data if d.get("document_id")]
        if doc_uuids:
            r_meta = supabase.table(SUPABASE_TABLE).select("id, volume_name").in_("id", doc_uuids).execute()
            name_map = {item["id"]: item["volume_name"] for item in r_meta.data}
            for d in vector_data:
                doc_id = d.get("document_id")
                if not d.get("metadata"):
                    d["metadata"] = {}
                if doc_id in name_map:
                    d["metadata"]["volume_name"] = name_map[doc_id]

        # Combine results while keeping richer vector metadata when a title hit
        # and a vector hit point to the same document.
        combined_data = merge_doc_candidates(keyword_data + vector_data)
        if not combined_data:
            raise ValueError("No results from search")
            
        # Deduplicate by document_id to avoid repeating the same document
        unique_docs = []
        seen_ids = set()
        for d in combined_data:
            doc_id = d.get("document_id")
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_docs.append(d)
                if len(unique_docs) >= 5: # Keep up to 5 unique documents
                    break
        
        return unique_docs
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        # Fallback: return recent docs
        result = supabase.table(SUPABASE_TABLE)\
            .select("id,doc_id,volume_name,translated_text,image_paths")\
            .limit(MATCH_COUNT)\
            .execute()
        # Normalize to same schema as RPC result
        docs = result.data or []
        return [{
            "document_id": d.get("id"),
            "content": (d.get("translated_text") or "")[:600],
            "metadata": {
                "volume_name": d.get("volume_name", ""),
                "image_paths": d.get("image_paths", []),
            },
            "similarity": 0.0,
        } for d in docs]


def get_doc_images(document_uuid: str) -> tuple:
    """Fetch volume_name + image_paths + content from main table by UUID."""
    try:
        r = supabase.table(SUPABASE_TABLE)\
            .select("volume_name,image_paths,translated_text")\
            .eq("id", document_uuid)\
            .limit(1)\
            .execute()
        if r.data:
            d = r.data[0]
            return d.get("volume_name", ""), d.get("image_paths") or [], d.get("translated_text") or ""
    except Exception as e:
        logger.warning(f"Could not fetch doc images for {document_uuid}: {e}")
    return "", [], ""


def find_matching_image_path(paths: List[str], meta: Dict[str, Any]) -> Optional[str]:
    page_key = str(meta.get("page_key") or "").strip()
    if page_key:
        needle = f"/page_key/{page_key}"
        for path in paths:
            if needle in path or path.endswith(f"/{page_key}.jpg") or path.endswith(f"/{page_key}.png"):
                return path

    page_number = meta.get("page_number")
    if page_number not in (None, "", 0, "0"):
        page_token = f"page_{int(page_number):04d}"
        for path in paths:
            if page_token in path:
                return path

    page_start = meta.get("page_start")
    if page_start not in (None, "", 0, "0"):
        page_token = f"page_{int(page_start):04d}"
        for path in paths:
            if page_token in path:
                return path

    return None


def get_display_page_from_path(paths: List[str], matched_path: Optional[str], meta: Dict[str, Any]) -> Optional[str]:
    if matched_path:
        try:
            return str(paths.index(matched_path) + 1)
        except ValueError:
            pass
    return get_page_value(meta)


def build_context(docs: List[dict]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.get("metadata") or {}
        vol = meta.get("volume_name") or meta.get("sutra_name", "") or ""
        page = get_page_value(meta)
        summary = meta.get("summary", "")
        content = doc.get("content") or ""
        context_text = (summary or content)[:600]
        if page:
            parts.append(f"[경전 {i}] {vol} (page={page})\n{context_text}")
        else:
            parts.append(f"[경전 {i}] {vol}\n{context_text}")
    return "\n\n".join(parts)


# ── Routes ────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    index = os.path.join(frontend_path, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "ok", "message": "정암 API running"}


@app.get("/mobile.html")
async def mobile_page():
    mobile = os.path.join(frontend_path, "mobile.html")
    if os.path.exists(mobile):
        return FileResponse(mobile)
    raise HTTPException(status_code=404, detail="Mobile page not found")


@app.get("/favicon.ico")
async def favicon():
    icon = os.path.join(frontend_path, "logo.png")
    if os.path.exists(icon):
        return FileResponse(icon, media_type="image/png")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/api/health")
async def health():
    return {"status": "healthy", "model": CHAT_MODEL}


@app.post("/api/tts")
async def tts(req: TTSRequest, background_tasks: BackgroundTasks):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    tts_python = os.getenv(
        "MINDBUDDHI_TTS_PYTHON",
        r"C:\Users\math\anaconda3\envs\mathwi\python.exe",
    )
    if not os.path.exists(tts_python):
        raise HTTPException(status_code=503, detail="Local XTTS Python environment not found")

    output = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    output_path = output.name
    output.close()

    env = os.environ.copy()
    env["COQUI_TOS_AGREED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [
        tts_python,
        os.path.join(os.getcwd(), "tts_infer_once.py"),
        "--text",
        text[:700],
        "--language",
        (req.language or "ko")[:2],
        "--output",
        output_path,
    ]

    try:
        subprocess.run(
            cmd,
            cwd=os.getcwd(),
            env=env,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=504, detail="Local XTTS generation timed out")
    except subprocess.CalledProcessError as exc:
        if os.path.exists(output_path):
            os.remove(output_path)
        logger.error("XTTS generation failed: %s", exc.stderr or exc.stdout)
        raise HTTPException(status_code=500, detail="Local XTTS generation failed")

    background_tasks.add_task(os.remove, output_path)
    return FileResponse(output_path, media_type="audio/wav", filename="mindbuddhi_buddi.wav")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="메시지를 입력해주세요.")

    try:
        # 1. Embed user query
        embedding = get_embedding(req.message)

        # 2. Retrieve relevant docs from Supabase
        docs = get_relevant_docs(embedding, req.message)

        # 3. Build context string
        context = build_context(docs)

        # 4. Select prompt based on track
        if req.track == "inquiry":
            system_prompt = INQUIRY_PROMPT
        elif req.track == "saju":
            system_prompt = SAJU_PROMPT
        elif req.track == "personality":
            system_prompt = PERSONALITY_PROMPT
        else:
            system_prompt = COUNSELING_PROMPT
            
        # Process language headers
        if req.lang == "en":
            system_prompt = system_prompt.replace("🌿 따뜻한 보듬음 (Compassionate Embrace)", "🌿 Compassionate Embrace")
            system_prompt = system_prompt.replace("📖 붓다의 지혜 (Wisdom of the Buddha)", "📖 The Buddha's Wisdom")
            system_prompt = system_prompt.replace("🧘 일상의 수행 (Daily Practice)", "🧘 Daily Practice")
            system_prompt = system_prompt.replace("🕯️ 지혜의 등불 (Lamp of Wisdom)", "🕯️ Lamp of Wisdom")
        else:
            system_prompt = system_prompt.replace("🌿 따뜻한 보듬음 (Compassionate Embrace)", "🌿 따뜻한 보듬음")
            system_prompt = system_prompt.replace("📖 붓다의 지혜 (Wisdom of the Buddha)", "📖 붓다의 지혜")
            system_prompt = system_prompt.replace("🧘 일상의 수행 (Daily Practice)", "🧘 일상의 수행")
            system_prompt = system_prompt.replace("🕯️ 지혜의 등불 (Lamp of Wisdom)", "🕯️ 지혜의 등불")

        # 5. Build messages for GPT
        resp_lang = "English" if req.lang == "en" else "Korean"
        system_msg = system_prompt + f"\n\nCRITICAL: You MUST respond in {resp_lang}."
        messages = [{"role": "system", "content": system_msg}]

        # If personality track, prepend user profile context
        if req.track == "personality" and (req.mbti or req.zodiac):
            profile_parts = []
            if req.mbti:
                profile_parts.append(f"MBTI: {req.mbti.upper()}")
            if req.zodiac:
                profile_parts.append(f"별자리: {req.zodiac}")
            profile_context = ", ".join(profile_parts)
            messages[0]["content"] += f"\n\n[사용자 성격 프로파일]\n{profile_context}"

        # Add conversation history (last 6 turns)
        for h in (req.history or [])[-6:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": h["content"]})

        # Add current query with context
        user_content = f"""[검색된 경전 구절]\n{context}\n\n[사용자 질문]\n{req.message}"""
        messages.append({"role": "user", "content": user_content})

        # 5. Generate response
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=600,
        )
        answer = response.choices[0].message.content


        # 6. Sources
        sources = []
        for d in docs:
            sim = d.get("similarity", 0)
            try:
                sim_val = round(float(sim), 3) if sim and str(sim) != 'NaN' else 0.0
            except (TypeError, ValueError):
                sim_val = 0.0
            meta = d.get("metadata") or {}
            vol = meta.get("volume_name") or meta.get("sutra_name", "")
            if not vol and d.get("document_id"):
                vol = f"경전 {str(d.get('document_id'))[:8]}"
            page = get_page_value(meta)
            label = build_source_label(vol or "경전 구절", meta, req.lang)
            
            sources.append({
                "volume": vol or "경전 구절",
                "label": label,
                "page": page,
                "doc_id": d.get("document_id", ""),
                "similarity": sim_val,
            })

        # Post-process to replace placeholders with actual source names
        # Handles variations: [경전 1], 경전 1, [출처: 경전 1] etc.
        import re
        
        def replace_indexed_source(match):
            try:
                # Use group(1) since our regexes now only have one capture group for the ID/Index
                raw_idx = match.group(1).lower()
                # 1. Digit matching (e.g., '1' from '경전 1')
                idx = -1
                if raw_idx.isdigit():
                    idx = int(raw_idx) - 1
                
                # 2. ID prefix matching
                else:
                    for i, s in enumerate(sources):
                        s_id = s.get("doc_id", "").lower()
                        if s_id.startswith(raw_idx) or raw_idx in s_id:
                            idx = i
                            break
                
                if 0 <= idx < len(sources):
                    return sources[idx]['label']
                return sources[0]["label"] if sources else "불교 경전"
            except:
                pass
            return match.group(0)

        # This will replace the whole thing like [출처: 경전 1] -> [중아함경 5쪽]
        # We ensure it result in exactly one pair of brackets: [Name Page쪽]
        answer = re.sub(r'[\[\(]*\s*출처:\s*경전\s*[\[\(\s]*([0-9a-zA-Z-]+)[\]\)\s]*\s*[\]\)]*', lambda m: f"[{replace_indexed_source(m)}]", answer)
        # Handle cases where AI just writes "경전 1" or "[경전 1]"
        answer = re.sub(r'[\[(]?\s*경전\s*([0-9a-zA-Z-]+)\s*[\])]?', lambda m: f"[{replace_indexed_source(m)}]", answer)

        # 6.5 Semantic Highlighting (Cosine Similarity)
        answer_emb = None
        try:
            # Only embed for semantic highlighting if answer is not too huge
            if answer and len(answer) < 3000:
                answer_emb = get_embedding(answer)
        except Exception as e:
            logger.warning(f"Failed to get answer embedding: {e}")
        
        # 7. Collect image URLs and identify highlight sentences
        # Prefer documents explicitly cited in the final answer to reduce source/image mismatch.
        cited_doc_ids: List[str] = []
        for s in sources:
            label = s.get("label") or ""
            vol = s.get("volume") or ""
            doc_id = s.get("doc_id") or ""
            if doc_id and (label in answer or vol in answer or f"[{vol}]" in answer or f"[{label}]" in answer):
                if doc_id not in cited_doc_ids:
                    cited_doc_ids.append(doc_id)

        ordered_doc_ids: List[str] = list(cited_doc_ids)
        # Add up to 5 docs that might not have been explicitly cited as fallback
        for doc in docs[:5]:
            doc_id = doc.get("document_id")
            if doc_id and doc_id not in ordered_doc_ids:
                ordered_doc_ids.append(doc_id)

        images: List[ImageResult] = []
        seen_image_urls: set = set()
        seen_paths: set = set()
        
        for doc_uuid in ordered_doc_ids:
            if len(images) >= 5:
                break
            
            d = next((item for item in docs if item.get("document_id") == doc_uuid), {})
            meta = d.get("metadata") or {}
            
            vol_name, doc_paths, _ = get_doc_images(doc_uuid)
            # Prioritize the specific content chunk for this page over the entire volume's translation
            text_to_split = d.get("content") or ""
            text_to_split = re.sub(r'\s+', ' ', text_to_split).strip()
            
            # Sentence extraction and scoring
            sentence_highlights = []
            raw_sentences = re.split(r'(?<=[.\?\!])\s+', text_to_split)
            sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 10]
            if sentences and answer_emb:
                try:
                    emb_res = openai_client.embeddings.create(model=EMBED_MODEL, input=sentences)
                    scores = []
                    for i, emb_data in enumerate(emb_res.data):
                        sim = cosine_similarity(answer_emb, emb_data.embedding)
                        scores.append((sentences[i], sim))
                    scores.sort(key=lambda x: x[1], reverse=True)
                    sentence_highlights = [s[0] for s in scores[:2] if s[1] > 0.3]
                except Exception as e:
                    logger.error(f"Sentence embedding failed: {e}")

            image_url = _normalize_public_image_url(meta.get("image_url"))
            display_page = get_page_value(meta)

            if not image_url:
                candidate_path = find_matching_image_path(doc_paths, meta)
                display_page = get_display_page_from_path(doc_paths, candidate_path, meta)
                if not candidate_path:
                    # try to get from docs root or meta
                    img_list = d.get("image_paths") or meta.get("image_paths") or doc_paths or []
                    if img_list:
                        candidate_path = img_list[0]
                        display_page = get_display_page_from_path(img_list, candidate_path, meta)
                if candidate_path:
                    image_url = get_image_url(candidate_path)
            
            if image_url and image_url in seen_image_urls:
                continue

            vol = meta.get("volume_name") or meta.get("sutra_name", "") or vol_name or "경전"
            base_book = get_translated_book_name(vol, req.lang)
            label = base_book
            if display_page:
                label = f"{base_book} Page {display_page}" if req.lang == "en" else f"{base_book} {display_page}쪽"

            if not image_url:
                image_url = f"data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7#{doc_uuid}"
            else:
                seen_image_urls.add(image_url)
            images.append(ImageResult(
                url=image_url,
                alt=label,
                translation=text_to_split,
                highlights=sentence_highlights
            ))

        return ChatResponse(answer=answer, sources=sources, images=images)

    except openai.OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        raise HTTPException(status_code=502, detail=f"AI 오류: {str(e)}")
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")
