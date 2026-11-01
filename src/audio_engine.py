import argparse
import os

# Automatically accept Coqui TTS terms of service to prevent the script from asking for [y/n] input
os.environ["COQUI_TOS_AGREED"] = "1"

from TTS.api import TTS

class AudioEngine:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
        print(f"Loading TTS Model: {model_name}...")
        # We load it to CPU since standard GitHub runners don't have GPUs
        self.tts = TTS(model_name).to("cpu")
        print("TTS Model loaded successfully.")

    def generate_audio(self, text, output_path, voice_option="default", clone_audio_path=None):
        if not text:
            print("No text provided. Skipping audio generation.")
            return None

        if not voice_option:
            voice_option = "default_male"

        print(f"Generating audio for text: '{text[:20]}...'")

        if clone_audio_path and os.path.exists(clone_audio_path):
            print(f"Cloning voice from: {clone_audio_path}")
            self.tts.tts_to_file(
                text=text, 
                speaker_wav=clone_audio_path, 
                language="en", 
                file_path=output_path
            )
        else:
            print(f"Using standard voice: {voice_option}")
            speaker = "Damien Black" if "male" in voice_option else "Claribel Dervla"
            
            self.tts.tts_to_file(
                text=text, 
                speaker=speaker, 
                language="en", 
                file_path=output_path
            )
            
        print(f"Audio saved to {output_path}")
        return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Audio from Text.")
    parser.add_argument("--text", required=True, help="Text to speak")
    parser.add_argument("--output", default="output.wav", help="Output file path")
    parser.add_argument("--voice", default="default_male", help="Voice option")
    parser.add_argument("--clone", default=None, help="Path to reference audio for cloning")
    
    args = parser.parse_args()
    
    engine = AudioEngine()
    engine.generate_audio(args.text, args.output, args.voice, args.clone)
