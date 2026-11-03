import argparse
import subprocess
import os
import textwrap

class VideoEngine:
    def __init__(self):
        pass

    def get_media_info(self, path):
        """Gets duration, width, and height of a media file."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=width,height", "-of", "default=noprint_wrappers=1", path
        ]
        try:
            output = subprocess.check_output(cmd).decode("utf-8")
            info = {}
            for line in output.strip().split("\n"):
                if "=" in line:
                    k, v = line.split("=", 1)
                    info[k] = float(v) if "." in v else int(v)
            return info
        except Exception:
            return {"duration": 3.0, "width": 1080, "height": 1920}

    def create_scene_clip(self, image_path, audio_path, output_path, width=1080, height=1920, motion="none", caption="", font_path="workspace/font.ttf"):
        print(f"Creating scene clip: {output_path} | Size: {width}x{height} | Motion: {motion}", flush=True)
        
        audio_info = self.get_media_info(audio_path)
        raw_duration = audio_info.get("duration", 3.0)
        
        # Add 0.5s silence pad at end so crossfade doesn't cut off speech
        padded_duration = raw_duration + 0.5
        frames = int(padded_duration * 25)
        
        # 1. Base scale: Prescale to 1.5x resolution to allow smooth Ken Burns movement
        base_w, base_h = int(width * 1.5), int(height * 1.5)
        filters = [
            f"scale={base_w}:{base_h}:force_original_aspect_ratio=increase,crop={base_w}:{base_h}"
        ]
        
        # 2. Dynamic Ken Burns Math (Calculated across total frames 'd')
        if motion == "zoom_in":
            filters.append(f"zoompan=z='1.0+0.25*(on/d)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:s={width}x{height}:fps=25")
        elif motion == "zoom_out":
            filters.append(f"zoompan=z='1.25-0.25*(on/d)':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={frames}:s={width}x{height}:fps=25")
        elif motion == "pan_right":
            filters.append(f"zoompan=z='1.20':x='(iw-iw/zoom)*(on/d)':y='(ih-ih/zoom)/2':d={frames}:s={width}x{height}:fps=25")
        elif motion == "pan_left":
            filters.append(f"zoompan=z='1.20':x='(iw-iw/zoom)*(1-on/d)':y='(ih-ih/zoom)/2':d={frames}:s={width}x{height}:fps=25")
        else:
            filters.append(f"fps=25,scale={width}:{height}")

        # 3. Captions with auto-wrap
        if caption:
            caption_file = output_path.replace(".mp4", "_caption.txt")
            wrap_width = 30 if width < height else 50
            wrapped_caption = "\n".join(textwrap.wrap(caption, width=wrap_width))
            with open(caption_file, "w", encoding="utf-8") as f:
                f.write(wrapped_caption)
            
            fontsize = 48 if width < height else 56
            filters.append(
                f"drawtext=fontfile='{font_path}':textfile='{caption_file}':"
                f"fontcolor=white:fontsize={fontsize}:box=1:boxcolor=black@0.6:boxborderw=15:"
                f"x=(w-text_w)/2:y=h-th-120:text_align=M"
            )

        vf_string = ",".join(filters)

        # -af apad adds 0.5s of audio padding
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-vf", vf_string,
            "-af", "apad=pad_dur=0.5",
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-t", str(padded_duration), output_path
        ]
        
        subprocess.run(cmd)
        return output_path

    def concatenate_clips(self, clip_paths, final_output_path, bgm_path=None, transition="fade"):
        print(f"Stitching {len(clip_paths)} scenes together with transition: {transition}...", flush=True)
        
        if len(clip_paths) == 1 or transition == "none":
            # Simple direct concat if 1 clip or transition is none
            list_file = "clips_list.txt"
            with open(list_file, "w") as f:
                for c in clip_paths:
                    f.write(f"file '{c}'\n")
            temp_output = "temp_merged.mp4"
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", temp_output])
            os.remove(list_file)
        else:
            # TRUE CROSSFADE (xfade)
            durations = [self.get_media_info(c).get("duration", 3.0) for c in clip_paths]
            trans_dur = 0.5 # 0.5 second smooth crossfade
            
            inputs = []
            for c in clip_paths:
                inputs.extend(["-i", c])
                
            filter_v = ""
            filter_a = ""
            current_offset = 0.0
            
            # Dynamically build the xfade chain
            last_v = "[0:v]"
            last_a = "[0:a]"
            
            for i in range(1, len(clip_paths)):
                current_offset += durations[i - 1] - trans_dur
                next_v = f"[{i}:v]"
                next_a = f"[{i}:a]"
                out_v = f"[v{i}]" if i < len(clip_paths) - 1 else "[vout]"
                out_a = f"[a{i}]" if i < len(clip_paths) - 1 else "[aout]"
                
                filter_v += f"{last_v}{next_v}xfade=transition=fade:duration={trans_dur}:offset={current_offset:.2f}{out_v};"
                filter_a += f"{last_a}{next_a}acrossfade=d={trans_dur}{out_a};"
                
                last_v = out_v
                last_a = out_a
                
            filter_complex = filter_v + filter_a
            temp_output = "temp_merged.mp4"
            
            cmd = ["ffmpeg", "-nostdin", "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[vout]", "-map", "[aout]",
                "-c:v", "libx264", "-c:a", "aac", temp_output
            ]
            subprocess.run(cmd)

        # Mix Background Music (BGM)
        if not bgm_path or not os.path.exists(bgm_path):
            os.rename(temp_output, final_output_path)
        else:
            print("Mixing background music...", flush=True)
            bgm_cmd = [
                "ffmpeg", "-nostdin", "-y", "-i", temp_output, "-stream_loop", "-1", "-i", bgm_path,
                "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.15[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:v", "copy", "-c:a", "aac", final_output_path
            ]
            subprocess.run(bgm_cmd)
            os.remove(temp_output)
            
        print(f"Final video generated: {final_output_path}", flush=True)
        return final_output_path
