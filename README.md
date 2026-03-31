How to use
* requires python: python 3.12 recommended

1. Pull or download repo
2. In the **.env.example** file, enter your API key (if you don't have one, see below for how to get one)
3. Save and rename **".env.example"** to **".env"**
4. Edit the text in **input_text.txt** to match what you want the TTS model to say. *Recommended to keep the current tags at the start of each line.*
5. Save **input_text.txt**
6. Run **create_tts.py**
7. Check **audio_out** folder in the folder where you ran **create_tts.py**; an mp3 file should be there
8. Settings can be adjusted by changing values in **.env** file

How to get API key
1. Login to ElevenLabs at https://elevenlabs.io/
2. Go to https://elevenlabs.io/app/developers/api-keys
3. Click "create key"
4. Give yourself necessary permissions
5. Click "create key" at the bottom of the list
6. Copy the key it gives you, paste it into your .env file after ELEVENLABS_API_KEY= (also highly recommended to save the key elsewhere)
