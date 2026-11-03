import argparse
import os
import json
import random
import requests

os.environ["COQUI_TOS_AGREED"] = "1"

import torch
torch.set_num_threads(1)

from TTS.api import TTS

# Curated list of high quality built-in XTTS v2 voices
BUILTIN_VOICES = [
    "Damien Black", "Claribel Dervla", "Gracie Wise", "Baldur Sanjin", 
    "Craig Gutsy", "Andrew Chipper", "Wulf Carlevaro", "Gilberto Mathias", 
    "Viktor Eka", "Ana Florence", "Daisy Studious", "Nova Hogarth", 
    "Annmarie Nele", "Sofia Hellen"
]

class AudioEngine:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2", registry_path="voices.json"):
        print(f"Initializing TTS class for {model_name}...", flush=True)
        self.tts = TTS(model_name).to("cpu")
        print("TTS Model fully loaded into memory successfully!", flush=True)
        
        self.voice_registry = {}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    self.voice_registry = json.load(f)
                print(f"Loaded {len(self.voice_registry)} cloned voices from {registry_path}", flush=True)
            except Exception as e:
                print(f"Warning: Could not read {registry_path}: {e}", flush=True)

    def resolve_speaker(self, speaker_name, workspace_dir="workspace"):
        """
        Determines whether the speaker is a built-in voice, a clone, or falls back to random.
        Returns: (voice_name, clone_audio_path)
        """
        clean_name = speaker_name.strip()
        
        # 1. Check if it matches a built-in AI voice (case-insensitive)
        for voice in BUILTIN_VOICES:
            if voice.lower() == clean_name.lower():
                print(f"Using built-in voice: {voice}", flush=True)
                return voice, None

        # 2. Check if it is in voices.json
        for registered_name, url in self.voice_registry.items():
            if registered_name.lower() == clean_name.lower():
                print(f"Found clone registry entry for '{clean_name}': {url}", flush=True)
                local_clone_path = os.path.join(workspace_dir, f"clone_{registered_name.replace(' ', '_')}.wav")
                if not os.path.exists(local_clone_path):
                    print(f"Downloading clone sample for {clean_name}...", flush=True)
                    r = requests.get(url, timeout=30)
                    with open(local_clone_path, "wb") as f:
                        f.write(r.content)
                return clean_name, local_clone_path

        # 3. Fallback: Pick a random built-in AI voice
        fallback_voice = random.choice(BUILTIN_VOICES)
        print(f"Speaker '{clean_name}' not found. Falling back to random voice: {fallback_voice}", flush=True)
        return fallback_voice, None

    def generate_audio(self, text, output_path, speaker_name="Damien Black"):
        if not text:
            return None

        voice, clone_path = self.resolve_speaker(speaker_name)
        print(f"Generating audio for '{text[:25]}...' with speaker: {speaker_name}", flush=True)

        if clone_path and os.path.exists(clone_path):
            self.tts.tts_to_file(
                text=text, 
                speaker_wav=clone_path, 
                language="en", 
                file_path=output_path
            )
        else:
            self.tts.tts_to_file(
                text=text, 
                speaker=voice, 
                language="en", 
                file_path=output_path
            )
            
        print(f"Audio successfully saved to {output_path}", flush=True)
        return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Audio from Text.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--speaker", default="Damien Black")
    parser.add_argument("--output", default="output.wav")
    args = parser.parse_args()

    engine = AudioEngine()
    engine.generate_audio(args.text, args.output, args.speaker)
