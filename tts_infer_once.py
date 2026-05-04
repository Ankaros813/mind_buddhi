import argparse
import os
import sys
import unicodedata

from TTS.api import TTS


MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
REFERENCE_WAV = os.path.join("tts_assets", "reference", "buddhi_ref_05m.wav")


def clean_tts_text(text: str) -> str:
    cleaned = []
    for char in text:
        category = unicodedata.category(char)
        if category in {"So", "Sk", "Cs", "Co", "Cn"}:
            cleaned.append(" ")
        else:
            cleaned.append(char)
    return " ".join("".join(cleaned).split())


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", default="ko")
    parser.add_argument("--output", required=True)
    parser.add_argument("--speaker-wav", default=REFERENCE_WAV)
    args = parser.parse_args()

    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    tts = TTS(MODEL_NAME).to("cuda")
    text = clean_tts_text(args.text[:700])
    tts.tts_to_file(
        text=text,
        speaker_wav=args.speaker_wav,
        language=args.language[:2],
        file_path=args.output,
    )
    print(MODEL_NAME)


if __name__ == "__main__":
    main()
