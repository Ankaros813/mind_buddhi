import io
import os
import threading

import soundfile as sf
from flask import Flask, jsonify, request, send_file


MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
REFERENCE_WAV = os.path.join("tts_assets", "reference", "buddhi_ref_05m.wav")
DEVICE = "cuda"

app = Flask(__name__)
_tts = None
_lock = threading.Lock()


def get_tts():
    global _tts
    if _tts is None:
        from TTS.api import TTS

        os.environ.setdefault("COQUI_TOS_AGREED", "1")
        _tts = TTS(MODEL_NAME).to(DEVICE)
    return _tts


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "model": MODEL_NAME, "voice": "buddi", "device": DEVICE})


@app.route("/api/tts", methods=["OPTIONS", "POST"])
def synthesize():
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or "").strip()
    language = str(data.get("language") or "ko").strip()[:2]
    if not text:
        return jsonify({"error": "text is required"}), 400

    text = text[:700]
    with _lock:
        wav = get_tts().tts(text=text, speaker_wav=REFERENCE_WAV, language=language)

    buffer = io.BytesIO()
    sf.write(buffer, wav, 24000, format="WAV")
    buffer.seek(0)
    return send_file(buffer, mimetype="audio/wav", download_name="mindbuddhi_buddi.wav")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8020, threaded=False, use_reloader=False)
