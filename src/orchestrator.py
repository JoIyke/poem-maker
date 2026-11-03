import json
import argparse
import os
from utils import download_file, create_fallback_image, send_webhook, download_font
from audio_engine import AudioEngine
from video_engine import VideoEngine

font_path = download_font("workspace/font.ttf")

def process_job(json_payload_path):
    print(f"Reading payload from {json_payload_path}")
    with open(json_payload_path, 'r') as f:
        job_data = json.load(f)

    # 1. Extract global settings with defaults
    webhook_url = job_data.get("webhook_url", "")
    bgm_url = job_data.get("bgm_url", "")
    global_voice = job_data.get("global_voice", "default_male")
    scenes = job_data.get("scenes", [])

    if not scenes:
        print("No scenes provided in JSON. Exiting.")
        return

    # Create workspace directories
    os.makedirs("workspace", exist_ok=True)
    
    # 2. Download BGM if provided
    bgm_path = None
    if bgm_url:
        bgm_path = download_file(bgm_url, "workspace/bgm.mp3")

    # 3. Initialize Engines (Loads heavy AI model into RAM just once)
    print("Initializing Engines...")
    audio_engine = AudioEngine()
    video_engine = VideoEngine()

    scene_clips = []

    # 4. Process each scene
    for i, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {i+1}/{len(scenes)} ---", flush=True)
        
        text = scene.get("text", "")
        image_url = scene.get("image_url", "")
        voice_option = scene.get("voice_option") or global_voice
        clone_url = scene.get("clone_url", "")
        
        # NEW PARAMS: Get the layout preferences (with fallbacks)
        motion = scene.get("motion", "none") 
        transition = scene.get("transition", "none")
        caption = scene.get("caption", "")

        # A. Prepare Image
        img_path = f"workspace/scene_{i}_img.jpg"
        if image_url:
            download_file(image_url, img_path)
            if not os.path.exists(img_path): 
                create_fallback_image(img_path)
        else:
            create_fallback_image(img_path)

        # B. Prepare Voice Clone (if any)
        clone_path = None
        if clone_url:
            clone_path = f"workspace/scene_{i}_clone.wav"
            download_file(clone_url, clone_path)

        # C. Generate Audio
        audio_path = f"workspace/scene_{i}_audio.wav"
        audio_engine.generate_audio(
            text=text, 
            output_path=audio_path, 
            voice_option=voice_option, 
            clone_audio_path=clone_path
        )

        # D. Combine into Scene Video (Now passing new options)
        clip_path = f"workspace/scene_{i}_clip.mp4"
        if os.path.exists(audio_path) and os.path.exists(img_path):
            video_engine.create_scene_clip(
                image_path=img_path, 
                audio_path=audio_path, 
                output_path=clip_path,
                motion=motion,
                caption=caption,
                transition=transition,
                font_path=font_path
            )
            scene_clips.append(clip_path)
        else:
            print(f"Skipping scene {i} compilation due to missing audio or image.", flush=True)

    # 5. Final Assembly
    if not scene_clips:
        print("No valid scenes generated. Aborting.")
        return

    final_video_path = "workspace/final_poem.mp4"
    video_engine.concatenate_clips(scene_clips, final_video_path, bgm_path)

    # 6. Delivery
    if os.path.exists(final_video_path):
        send_webhook(webhook_url, final_video_path)
    else:
        print("Error: Final video was not created.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate the video generation.")
    parser.add_argument("--payload", required=True, help="Path to the JSON payload file")
    
    args = parser.parse_args()
    process_job(args.payload)
