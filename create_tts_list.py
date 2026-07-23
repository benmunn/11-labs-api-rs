import argparse
import csv
import os
import re
from pathlib import Path

import librosa
import numpy as np
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs


# ------------------------------------------------------------
# Environment helpers
# ------------------------------------------------------------

def require_env(name: str, cast=str):
    """
    Read a required environment variable and optionally cast it.
    """
    value = os.getenv(name)

    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")

    try:
        return cast(value)
    except ValueError:
        raise RuntimeError(
            f"Invalid value for environment variable {name}: {value}"
        )


def optional_env(name: str, default, cast=str):
    """
    Read an optional environment variable and optionally cast it.
    """
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return cast(value)
    except ValueError:
        raise RuntimeError(
            f"Invalid value for environment variable {name}: {value}"
        )


# ------------------------------------------------------------
# Text / filename helpers
# ------------------------------------------------------------

def clean_filename(text: str) -> str:
    """
    Convert a CSV entry into a safe filename.

    Example:
        "Get out!" -> "get-out.mp3"
        "go / went" -> "go-went.mp3"
    """

    text = text.strip().lower()

    # Remove bracketed tags from filenames, e.g. [slowly]
    text = re.sub(r"\[.*?\]", "", text)

    # Replace invalid Windows/macOS/Linux filename characters
    text = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "-", text)

    # Replace punctuation that tends to make ugly filenames
    text = re.sub(r"[.,;!(){}]", "", text)

    # Replace whitespace and underscores with hyphens
    text = re.sub(r"[\s_]+", "-", text)

    # Collapse repeated hyphens
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing dots, spaces, and hyphens
    text = text.strip(".- ")

    # Avoid extremely long filenames
    text = text[:120]

    if not text:
        raise ValueError("Cannot create filename from empty text.")

    return text


def get_output_path(output_dir: Path, text: str) -> Path:
    """
    Create the intended MP3 output path for a CSV entry.
    """
    filename = clean_filename(text)
    return output_dir / f"{filename}.mp3"


# ------------------------------------------------------------
# Audio validation
# ------------------------------------------------------------

def analyze_audio_file(
    file_path: Path,
    min_size_kb: float = 5,
    max_size_kb: float = 300,
    min_duration: float = 0.2,
    max_duration: float = 4.0,
    min_rms: float = 0.001,
    max_peak: float = 0.99,
):
    """
    Validate the generated MP3 file.

    Returns:
        (True, "Passed")
        or
        (False, "Reason")
    """

    if not file_path.exists():
        return False, "File does not exist"

    file_size_kb = file_path.stat().st_size / 1024

    if file_size_kb < min_size_kb:
        return False, f"File too small: {file_size_kb:.1f} KB"

    if file_size_kb > max_size_kb:
        return False, f"File too large: {file_size_kb:.1f} KB"

    try:
        y, sr = librosa.load(str(file_path), sr=None, mono=True)
    except Exception as e:
        return False, f"Could not load audio: {e}"

    if y.size == 0:
        return False, "Audio contains no samples"

    duration = librosa.get_duration(y=y, sr=sr)

    if duration < min_duration:
        return False, f"Audio too short: {duration:.2f}s"

    if duration > max_duration:
        return False, f"Audio too long: {duration:.2f}s"

    peak = float(np.max(np.abs(y)))
    rms = float(np.sqrt(np.mean(y ** 2)))

    if rms < min_rms:
        return False, f"Audio is silent or nearly silent. RMS: {rms:.6f}"

    if peak >= max_peak:
        return False, f"Possible clipping / pop artifact. Peak: {peak:.4f}"

    return True, "Passed"


# ------------------------------------------------------------
# ElevenLabs generation
# ------------------------------------------------------------

def generate_tts_file(
    client: ElevenLabs,
    text: str,
    output_path: Path,
    voice_id: str,
    model_id: str,
    output_format: str,
    stability: float,
    similarity_boost: float,
    style: float,
    speed: float,
):
    """
    Generate one MP3 file from one CSV entry.
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    response = client.text_to_speech.convert(
        voice_id=voice_id,
        output_format=output_format,
        text=text.strip(),
        model_id=model_id,
        voice_settings=VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            speed=speed,
        ),
    )

    with open(output_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    return output_path


def generate_and_validate(
    client: ElevenLabs,
    text: str,
    output_path: Path,
    settings: dict,
    max_attempts: int,
):
    """
    Generate an audio file and remake it if validation fails.
    """

    last_reason = None

    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}: {text}")

        try:
            generate_tts_file(
                client=client,
                text=text,
                output_path=output_path,
                **settings,
            )
        except Exception as e:
            last_reason = f"ElevenLabs generation failed: {e}"
            print(f"  Failed: {last_reason}")
            continue

        passed, reason = analyze_audio_file(output_path)

        if passed:
            print(f"  Passed: {output_path}")
            return True, "Passed"

        last_reason = reason
        print(f"  Failed validation: {reason}")

        # Remove bad file before trying again.
        try:
            output_path.unlink(missing_ok=True)
        except OSError:
            pass

    return False, last_reason or "Unknown failure"


# ------------------------------------------------------------
# CSV reading
# ------------------------------------------------------------

def read_one_column_csv(csv_path: Path, has_header: bool):
    """
    Read a 1-column CSV and return a list of entries.
    Empty rows are skipped.
    """

    entries = []

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        if has_header:
            next(reader, None)

        for line_number, row in enumerate(reader, start=2 if has_header else 1):
            if not row or not row[0].strip():
                print(f"Skipping empty row: line {line_number}")
                continue

            entry = row[0].strip()
            entries.append((line_number, entry))

    return entries


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate ElevenLabs MP3 files from a 1-column CSV, "
            "save each file using the entry name, and remake failed files."
        )
    )

    parser.add_argument(
        "csv_file",
        help="Path to the 1-column CSV file."
    )

    parser.add_argument(
        "--head",
        action="store_true",
        help="Skip the first row as a header."
    )

    parser.add_argument(
        "--out-root",
        default=".",
        help="Root output folder. Files are saved inside [out-root]/audio_out. Default: current folder."
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximum generation attempts per entry. Default: 5."
    )

    args = parser.parse_args()

    if args.max_attempts < 1:
        raise ValueError("--max-attempts must be at least 1")

    csv_path = Path(args.csv_file)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if not csv_path.is_file():
        raise ValueError(f"CSV path is not a file: {csv_path}")

    load_dotenv()

    api_key = require_env("ELEVENLABS_API_KEY")
    model_id = require_env("ELEVENLABS_MODEL_ID")
    voice_id = require_env("ELEVENLABS_VOICE_ID")

    stability = require_env("VOICE_SETTING_STABILITY", float)
    similarity_boost = require_env("VOICE_SETTING_SIMILARITY", float)
    style = require_env("VOICE_SETTING_STYLE_BOOST", float)
    speed = require_env("VOICE_SETTING_SPEED", float)

    output_format = optional_env(
        "AUDIO_OUTPUT_FORMAT",
        "mp3_44100_128",
        str,
    )

    if not output_format.startswith("mp3_"):
        raise RuntimeError(
            f"AUDIO_OUTPUT_FORMAT must be an MP3 format because files are saved as .mp3. "
            f"Current value: {output_format}"
        )

    client = ElevenLabs(api_key=api_key)

    settings = {
        "voice_id": voice_id,
        "model_id": model_id,
        "output_format": output_format,
        "stability": stability,
        "similarity_boost": similarity_boost,
        "style": style,
        "speed": speed,
    }

    output_dir = Path(args.out_root) / "audio_out"
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = read_one_column_csv(csv_path, args.head)

    if not entries:
        print("No valid entries found in CSV.")
        return

    failed_generations = []

    for line_number, text in entries:
        print(f"\nProcessing line {line_number}: {text}")

        try:
            output_path = get_output_path(output_dir, text)
        except ValueError as e:
            failed_generations.append(
                f"Line {line_number}: {text!r} failed before generation. Reason: {e}"
            )
            continue

        passed, reason = generate_and_validate(
            client=client,
            text=text,
            output_path=output_path,
            settings=settings,
            max_attempts=args.max_attempts,
        )

        if not passed:
            failed_generations.append(
                f"Line {line_number}: {text!r} failed after {args.max_attempts} attempts. "
                f"Reason: {reason}. Intended file: {output_path}"
            )

    print("\nDone.")

    if failed_generations:
        print("\nFailed generations:")
        for item in failed_generations:
            print(f"- {item}")
    else:
        print("All files generated and passed validation.")


if __name__ == "__main__":
    main()