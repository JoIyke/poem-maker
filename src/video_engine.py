import argparse
import subprocess
import os
import textwrap

class VideoEngine:
    def __init__(self):
        pass

    def get_audio_duration(self, audio_path):
        """Uses ffprobe to get the exact length of the audio file in seconds."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_path
        ]
        try:
            return float(subprocess.check_output(cmd).decode("utf-8").strip())
        except Exception:
            return 3.0 # Fallback 

    def create_scene_clip(self, image_path, audio_path, output_path, motion="none", caption="", transition="none", font_path="workspace/font.ttf"):
        print(f"Creating scene clip: {output_path} | Motion: {motion} | Transition: {transition}", flush=True)
        
        duration = self.get_audio_duration(audio_path)
        frames = int(duration * 25) # We lock the video to 25 FPS for smooth zooming
        
        # Step 1: Base scale to ensure ALL images fill the screen at 1920x1080 without distortion
        filters = ["scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"]
        
        # Step 2: Add Motion (Ken Burns)
        if motion == "zoom_in":
            filters.append(f"zoompan=z='min(zoom+0.001,1.5)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=25")
        elif motion == "zoom_out":
            filters.append(f"zoompan=z='max(1.5-0.001*in,1)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=25")
        elif motion == "pan_right":
            filters.append(f"zoompan=z='1.2':d={frames}:x='x+1':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=25")
        elif motion == "pan_left":
            filters.append(f"zoompan=z='1.2':d={frames}:x='if(eq(in,1),iw*0.2,x-1)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=25")
        else:
            # Even if no motion, explicitly set frame rate so concat doesn't crash later
            filters.append("fps=25,scale=1920:1080")

        # Step 3: Add Captions
        if caption:
            # We write the text to a temporary file. This prevents FFmpeg from crashing 
            # if your caption contains apostrophes, quotes, or special characters!
            caption_file = output_path.replace(".mp4", "_caption.txt")
            wrapped_caption = "\n".join(textwrap.wrap(caption, width=45)) # Auto-wrap long lines
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(wrapped_caption)
            
            # Draws text at Bottom-Center with a semi-transparent black background box
            filters.append(
                f"drawtext=fontfile='{font_path}':textfile='{caption_file}':"
                "fontcolor=white:fontsize=56:box=1:boxcolor=black@0.6:boxborderw=15:"
                "x=(w-text_w)/2:y=h-th-80:text_align=M"
            )

        # Step 4: Add Transitions
        if transition == "fade":
            fade_out_start = max(0, duration - 0.5)
            # Fade in from black for 0.5s, fade out to black for 0.5s
            filters.append(f"fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_start}:d=0.5")

        # Join all filters together with a comma
        vf_string = ",".join(filters)

        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-vf", vf_string,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", output_path
        ]
        
        subprocess.run(cmd)
        print(f"Finished creating {output_path}", flush=True)
        return output_path

    def concatenate_clips(self, clip_paths, final_output_path, bgm_path=None):
        print("Concatenating scenes together...", flush=True)
        list_file = "clips_list.txt"
        with open(list_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")

        temp_output = "temp_merged.mp4"
        concat_cmd = ["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", temp_output]
        subprocess.run(concat_cmd)

        if not bgm_path or not os.path.exists(bgm_path):
            os.rename(temp_output, final_output_path)
        else:
            print("Adding background music...", flush=True)
            bgm_cmd = [
                "ffmpeg", "-nostdin", "-y", "-i", temp_output, "-stream_loop", "-1", "-i", bgm_path,
                "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:v", "copy", "-c:a", "aac", final_output_path
            ]
            subprocess.run(bgm_cmd)
            os.remove(temp_output)
            
        os.remove(list_file)
        print(f"Final video saved to {final_output_path}", flush=True)
        return final_output_path
