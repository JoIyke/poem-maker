import json
import argparse
import os
import random
from utils import download_file, create_fallback_image, send_webhook, download_font
from audio_engine import AudioEngine
from video_engine import VideoEngine
from caption_engine import CaptionEngine

def parse_scene_text(raw_text):
    """
    Parses 'Speaker Name>Text' or defaults to Damien Black if no '>' is present.
    """
    if ">" in raw_text:
        speaker, text = raw_text.split(">", 1)
        return speaker.strip(), text.strip()
    return "Damien Black", raw_text.strip()

def process_job(json_payload_path):
    print(f"Reading payload from {json_payload_path}", flush=True)
    with open(json_payload_path, 'r') as f:
        job_data = json.load(f)

    webhook_url = job_data.get("webhook_url", "")
    bgm_url = job_data.get("bgm_url", "")
    caption_mode = str(job_data.get("caption", "animated")).lower()
    hook_text = job_data.get("hook_text", "")
    global_motion = job_data.get("motion", "random") 
    global_transition = job_data.get("transition", "fade")
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

    width, height = 1080, 1920
    if aspect_ratio in ["landscape", "16:9"]:
        width, height = 1920, 1080
    elif aspect_ratio in ["portrait", "9:16"]:
        width, height = 1080, 1920

    scene_clips = []
    scene_timeline = []
    current_time = 0.0
    trans_dur = 0.6 if global_transition == "fade" else 0.0

    motion_choices = ["zoom_in", "zoom_out", "pan_right", "pan_left"]

    for i, scene in enumerate(scenes):
        print(f"\n--- Processing Scene {i+1}/{len(scenes)} ---", flush=True)
        
        raw_text = scene.get("text", "")
        image_url = scene.get("image_url", "")

        # Extract Speaker Name and pure speech text
        speaker_name, clean_text = parse_scene_text(raw_text)

        current_motion = random.choice(motion_choices) if global_motion.lower() == "random" else global_motion
        current_caption = clean_text if caption_mode == "normal" else ""

        img_path = f"workspace/scene_{i}_img.jpg"
        if image_url:
            download_file(image_url, img_path)
            if not os.path.exists(img_path): 
                create_fallback_image(img_path, width, height)
        else:
            create_fallback_image(img_path, width, height)

        if i == 0 and aspect_ratio == "auto":
            info = video_engine.get_media_info(img_path)
            if info.get("width", 1080) >= info.get("height", 1920):
                width, height = 1920, 1080
            else:
                width, height = 1080, 1920

        # Generate Audio with the resolved speaker
        audio_path = f"workspace/scene_{i}_audio.wav"
        audio_engine.generate_audio(
            text=clean_text, 
            output_path=audio_path, 
            speaker_name=speaker_name
        )

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
                transition=global_transition,
                hook_text=hook_text
            )
            scene_clips.append(clip_path)

            # Track start & end timestamps of this speaker for captions
            clip_dur = video_engine.get_media_info(clip_path).get("duration", 3.0)
            scene_end = current_time + clip_dur - (trans_dur if i > 0 else 0.0)
            scene_timeline.append({
                "speaker": speaker_name,
                "start": current_time,
                "end": scene_end
            })
            current_time = scene_end

    if not scene_clips:
        print("No valid scenes generated. Aborting.", flush=True)
        return

    # 1. Assemble base video
    raw_video_path = "workspace/raw_video.mp4"
    video_engine.concatenate_clips(scene_clips, raw_video_path, bgm_path, transition=global_transition)

    final_video_path = "workspace/final_poem.mp4"

    # 2. Burn speaker-aware animated captions if requested
    if caption_mode == "animated":
        caption_engine = CaptionEngine()
        caption_engine.burn_captions(raw_video_path, final_video_path, scene_timeline, width=width, height=height)
    else:
        os.rename(raw_video_path, final_video_path)

    # 3. Delivery
    if os.path.exists(final_video_path):
        send_webhook(webhook_url, final_video_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrate the video generation.")
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    process_job(args.payload)
