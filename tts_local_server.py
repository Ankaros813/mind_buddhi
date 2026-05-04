import io
import os
import threading
import time
import unicodedata

import soundfile as sf
from flask import Flask, jsonify, request, send_file


MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
REFERENCE_WAV = os.path.join("tts_assets", "reference", "buddhi_ref_05m.wav")
DEVICE = "cuda"

app = Flask(__name__)
_tts = None
_voice_latents = None
_lock = threading.Lock()
_cache = {}
_cache_order = []
_cache_lock = threading.Lock()
_warmup_started_at = time.time()


def clean_tts_text(text: str) -> str:
    cleaned = []
    for char in text:
        category = unicodedata.category(char)
        if category in {"So", "Sk", "Cs", "Co", "Cn"}:
            cleaned.append(" ")
        else:
            cleaned.append(char)
    return " ".join("".join(cleaned).split())


def get_tts():
    global _tts
    if _tts is None:
        from TTS.api import TTS

        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        _tts = TTS(MODEL_NAME).to(DEVICE)
    return _tts


def get_voice_latents():
    global _voice_latents
    if _voice_latents is None:
        model = get_tts().synthesizer.tts_model
        _voice_latents = model.get_conditioning_latents(
            audio_path=REFERENCE_WAV,
            gpt_cond_len=6,
            gpt_cond_chunk_len=6,
            max_ref_length=10,
            sound_norm_refs=False,
        )
    return _voice_latents


def synthesize_xtts(text, language):
    model = get_tts().synthesizer.tts_model
    gpt_cond_latent, speaker_embedding = get_voice_latents()
    result = model.inference(
        text,
        language,
        gpt_cond_latent,
        speaker_embedding,
        temperature=0.65,
        length_penalty=1.0,
        repetition_penalty=10.0,
        top_k=30,
        top_p=0.8,
        do_sample=True,
        speed=1.06,
    )
    return result["wav"]


def cache_get(key):
    with _cache_lock:
        return _cache.get(key)


def cache_set(key, value):
    with _cache_lock:
        if key not in _cache:
            _cache_order.append(key)
        _cache[key] = value
        while len(_cache_order) > 64:
            old_key = _cache_order.pop(0)
            _cache.pop(old_key, None)


def warmup_model():
    try:
        with _lock:
            get_tts()
            get_voice_latents()
            synthesize_xtts("마음을 천천히 바라보세요.", "ko")
        app.logger.info("XTTS warmup completed in %.1fs", time.time() - _warmup_started_at)
    except Exception:
        app.logger.exception("XTTS warmup failed")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "model": MODEL_NAME,
            "voice": "buddi",
            "device": DEVICE,
            "model_loaded": _tts is not None,
            "voice_latents_loaded": _voice_latents is not None,
        }
    )


@app.route("/api/tts", methods=["OPTIONS", "POST"])
def synthesize():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    language = str(data.get("language") or "ko").strip()[:2]
    if not text:
        return jsonify({"error": "text is required"}), 400

    text = clean_tts_text(text[:220])
    cache_key = (text, language)
    cached = cache_get(cache_key)
    if cached:
        return send_file(
            io.BytesIO(cached),
            mimetype="audio/wav",
            download_name="mindbuddhi_buddi.wav",
        )

    with _lock:
        try:
            wav = synthesize_xtts(text, language)
        except Exception:
            app.logger.exception("Fast XTTS inference failed; falling back to speaker_wav path")
            wav = get_tts().tts(text=text, speaker_wav=REFERENCE_WAV, language=language)

    buffer = io.BytesIO()
    sf.write(buffer, wav, 24000, format="WAV")
    audio_bytes = buffer.getvalue()
    cache_set(cache_key, audio_bytes)
    buffer = io.BytesIO(audio_bytes)
    return send_file(buffer, mimetype="audio/wav", download_name="mindbuddhi_buddi.wav")


if __name__ == "__main__":
    threading.Thread(target=warmup_model, daemon=True).start()
    app.run(host="127.0.0.1", port=8020, threaded=False, use_reloader=False)
