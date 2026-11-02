import argparse
import os

# Automatically accept Coqui TTS terms of service
os.environ["COQUI_TOS_AGREED"] = "1"

# Force PyTorch to use only 1 CPU thread to prevent deadlocks
import torch
torch.set_num_threads(1)

from TTS.api import TTS

class AudioEngine:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
        print(f"Loading TTS Model: {model_name} (This may take 1-2 minutes)...", flush=True)
        self.tts = TTS(model_name).to("cpu")
        print("TTS Model loaded into memory successfully!", flush=True)

    def generate_audio(self, text, output_path, voice_option="default", clone_audio_path=None):
        if not text:
            print("No text provided. Skipping audio generation.", flush=True)
            return None

        if not voice_option:
            voice_option = "default_male"

        print(f"Generating audio for text: '{text[:20]}...' (Please wait, CPU generation is slow)", flush=True)

        if clone_audio_path and os.path.exists(clone_audio_path):
            print(f"Cloning voice from: {clone_audio_path}", flush=True)
            self.tts.tts_to_file(
                text=text, 
                speaker_wav=clone_audio_path, 
                language="en", 
                file_path=output_path
            )
        else:
            print(f"Using standard voice: {voice_option}", flush=True)
            speaker = "Damien Black" if "male" in voice_option else "Claribel Dervla"
            
            self.tts.tts_to_file(
                text=text, 
                speaker=speaker, 
                language="en", 
                file_path=output_path
            )
            
        print(f"Audio successfully saved to {output_path}", flush=True)
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
