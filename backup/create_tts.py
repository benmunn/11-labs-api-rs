
import os
import uuid
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


def tts_file(text: str) -> str:
    # Calling the text_to_speech conversion API with detailed parameters
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
       
    # create a filename based on the first few non-tag words in the input text
    fn_start = clean_title(text)

    # uncomment the line below to play the audio back
    # play(response)
    
    #creating an output folder
    os.makedirs("audio_out", exist_ok=True)
    
    # Generating a unique file name for the output MP3 file
    save_file_path = f"audio_out/{fn_start}_{uuid.uuid4()}.mp3"

    # Writing the audio to a file
    with open(save_file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print(f"{save_file_path}: A new audio file was saved successfully!")

    # Return the path of the saved audio file
    return save_file_path



def main():
    input_filename = "input_text.txt"
    input_text = None
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            input_text = f.read()
    except FileNotFoundError:
        print(f"{input_filename} not found")
    except UnicodeDecodeError:
        print("Error reading file with utf-8 encoding.")
    tts_file(input_text)

if __name__ == "__main__":
    main()