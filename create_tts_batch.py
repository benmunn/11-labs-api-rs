
import os
import uuid
import glob
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import re

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
VOICE_SETTING_STABILITY = float(os.getenv("VOICE_SETTING_STABILITY"))
VOICE_SETTING_SIMILARITY = float(os.getenv("VOICE_SETTING_SIMILARITY"))
VOICE_SETTING_STYLE_BOOST = float(os.getenv("VOICE_SETTING_STYLE_BOOST"))
VOICE_SETTING_SPEED = float(os.getenv("VOICE_SETTING_SPEED"))
AUDIO_OUTPUT_FORMAT = os.getenv("AUDIO_OUTPUT_FORMAT")
GENERATION_COUNT = int(os.getenv("GENERATION_COUNT"))

INPUT_DIR = "text_in"


elevenlabs = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

def clean_title(text: str) -> str:
    #removes spaces, tags,
    tag_pattern = r'\[.*?\]'
    space_pattern = r' '
    tags_removed = re.sub(tag_pattern, '', text)
    stripped = tags_removed.strip()
    spaces_removed = re.sub(space_pattern, '-', stripped)
    lowered = spaces_removed.lower()
    fn_start = None
    try:
        if len(lowered) < 10:
            fn_start = lowered
        else:
            fn_start = lowered[:10]
    except:
        raise ValueError("No text in input file. Please double check.")
    return fn_start


def tts_file(text: str, base_name: str) -> str:
    # use the source .txt filename (without extension) as the output name
    fn_start = base_name

    #creating an output folder
    os.makedirs("audio_out", exist_ok=True)

    save_file_path = None
    for _ in range(GENERATION_COUNT):
        # Calling the text_to_speech conversion API with detailed parameters.
        # The response is a one-shot iterator, so request a fresh one for each
        # generation to avoid writing empty files after the first pass.
        response = elevenlabs.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID, # Hope - upbeat and clear
            output_format=AUDIO_OUTPUT_FORMAT,
            text=text,
            model_id=ELEVENLABS_MODEL_ID,
            # Optional voice settings that allow you to customize the output
            voice_settings=VoiceSettings(
                stability=VOICE_SETTING_STABILITY,
                similarity_boost=VOICE_SETTING_SIMILARITY,
                style=VOICE_SETTING_STYLE_BOOST,
                speed=VOICE_SETTING_SPEED,
            ),
        )

        # Generating a unique file name for the output MP3 file
        save_file_path = f"audio_out/{fn_start}_{uuid.uuid4()}.mp3"
        save_file_path_noname = f"audio_out/{uuid.uuid4()}.mp3"

        # Writing the audio to a file
        try:
            with open(save_file_path, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            print(f"{save_file_path}: A new audio file was saved successfully!")
        except OSError:
            with open(save_file_path_noname, "wb") as f:
                for chunk in response:
                    if chunk:
                        f.write(chunk)
            print(f"{save_file_path_noname}: A new audio file was saved successfully!")


    # Return the path of the saved audio file
    return save_file_path



def main():
    if not os.path.isdir(INPUT_DIR):
        print(f"Input directory '{INPUT_DIR}' not found")
        return

    input_files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.txt")))
    if not input_files:
        print(f"No .txt files found in '{INPUT_DIR}'")
        return

    print(f"Found {len(input_files)} text file(s) in '{INPUT_DIR}'")

    for input_filename in input_files:
        print(f"\nProcessing {input_filename} ...")
        input_text = None
        try:
            with open(input_filename, 'r', encoding='utf-8') as f:
                input_text = f.read()
        except FileNotFoundError:
            print(f"{input_filename} not found")
            continue
        except UnicodeDecodeError:
            print(f"Error reading {input_filename} with utf-8 encoding.")
            continue

        if not input_text or not input_text.strip():
            print(f"{input_filename} is empty, skipping.")
            continue

        base_name = os.path.splitext(os.path.basename(input_filename))[0]
        tts_file(input_text, base_name)

if __name__ == "__main__":
    main()
