from elevenlabs.client import ElevenLabs

client = ElevenLabs(api_key="484f911ad1da0153629ca155b2dd9ec16628ba242777d7ba4c1d16f446427ead")

audio = client.text_to_speech.convert(
    voice_id="JBFqnCBsd6RMkjVDRZzb",  # "George" voice
    text="Welcome to our store. Check out our latest products!",
    model_id="eleven_multilingual_v2"
)

with open("test_voice.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("Done — check test_voice.mp3")