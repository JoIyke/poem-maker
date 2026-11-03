import json
import argparse
import os
import random
from utils import download_file, create_fallback_image, send_webhook, download_font
from audio_engine import AudioEngine
from video_engine import VideoEngine

def process_job(json_payload_path):
    print(f"Reading payload from {json_payload_path}", flush=True)
    with open(json_payload_path, 'r') as f:
        job_data = json.load(f)

    webhook_url = job_data.get("webhook_url", "")
    bgm_url = job_data.get("bgm_url", "")
    global_voice = job_data.get("global_voice", "default_male")
    
    caption_enabled = str(job_data.get("caption", "false")).lower() in ["true", "1", "yes"]
    global_motion = job_data.get("motion", "random") 
    global_transition = job_data.get("transition", "fade") # Default is now true crossfade!
    aspect_ratio = job_data.get("aspect_ratio", "auto").lower()

    scenes = job_data.get("scenes", [])
    if not scenes:
        print("No scenes provided in JSON. Exiting.", flush=True)
        return

    os.makedirs("workspace", exist_ok=True)
    
    bgm_path = download_file(bgm_url, "workspace/bgm.mp3") if bgm_url else None
    font_path = download_font("workspace/font.ttf")

    print("Initializing Engines...", flush=True)
    audio_engine = AudioEngine()
    video_engine = VideoEngine()

    # Determine Resolution (Portrait 1080x1920 vs Landscape 1920x1080)
    width, height = 1080, 1920 # Default Portrait (Vertical Shorts/Reels)
    if aspect_ratio in ["landscape", "16:9"]:
        width, height = 1920, 1080
    elif aspect_ratio in ["portrait", "9:16"]:
        width, height = 1080, 1920

    scene_clips = []
    motion_choices = ["zoom_in", "zoom_out", "pan_right", "pan_left"]

    for i, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {i+1}/{len(scenes)} ---", flush=True)
        
        text = scene.get("text", "")
        image_url = scene.get("image_url", "")
        voice_option = scene.get("voice_option") or global_voice
        clone_url = scene.get("clone_url", "")

        # Pick randomized motion
        current_motion = random.choice(motion_choices) if global_motion.lower() == "random" else global_motion
        current_caption = text if caption_enabled else ""

        # Prepare Image
        img_path = f"workspace/scene_{i}_img.jpg"
        if image_url:
            download_file(image_url, img_path)
            if not os.path.exists(img_path): 
                create_fallback_image(img_path, width, height)
        else:
            create_fallback_image(img_path, width, height)

        # Auto-detect resolution from the 1st image if aspect_ratio is 'auto'
        if i == 0 and aspect_ratio == "auto":
            info = video_engine.get_media_info(img_path)
            if info.get("width", 1080) >= info.get("height", 1920):
                width, height = 1920, 1080
                print(f"Auto-detected Landscape image: Setting video to 1920x1080", flush=True)
            else:
                width, height = 1080, 1920
                print(f"Auto-detected Portrait image: Setting video to 1080x1920", flush=True)

        # Prepare Voice Clone
        clone_path = None
        if clone_url:
            clone_path = f"workspace/scene_{i}_clone.wav"
            download_file(clone_url, clone_path)

        # Generate Audio
        audio_path = f"workspace/scene_{i}_audio.wav"
        audio_engine.generate_audio(
            text=text, 
            output_path=audio_path, 
            voice_option=voice_option, 
            clone_audio_path=clone_path
        )

        # Create Scene Clip
        clip_path = f"workspace/scene_{i}_clip.mp4"
        if os.path.exists(audio_path) and os.path.exists(img_path):
            video_engine.create_scene_clip(
                image_path=img_path, 
                audio_path=audio_path, 
                output_path=clip_path,
                width=width,
                height=height,
                motion=current_motion,
                caption=current_caption,
                font_path=font_path,
                is_first_scene=(i == 0),
                transition=global_transition
            )
            scene_clips.append(clip_path)


    if not scene_clips:
        print("No valid scenes generated. Aborting.", flush=True)
        return

    # Final Assembly with True Crossfade
    final_video_path = "workspace/final_poem.mp4"
    video_engine.concatenate_clips(scene_clips, final_video_path, bgm_path, transition=global_transition)

    if os.path.exists(final_video_path):
        send_webhook(webhook_url, final_video_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate the video generation.")
    parser.add_argument("--payload", required=True, help="Path to the JSON payload file")
    args = parser.parse_args()
    process_job(args.payload)
