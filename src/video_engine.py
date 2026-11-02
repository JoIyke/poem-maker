import argparse
import subprocess
import os

class VideoEngine:
    def __init__(self):
        pass

    def create_scene_clip(self, image_path, audio_path, output_path):
        print(f"Creating scene clip: {output_path}", flush=True)
        
        # Added -nostdin to prevent GitHub Actions from freezing, and removed DEVNULL to show logs
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
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
        
        concat_cmd = [
            "ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0", 
            "-i", list_file, "-c", "copy", temp_output
        ]
        subprocess.run(concat_cmd)

        if not bgm_path or not os.path.exists(bgm_path):
            print("No BGM provided or found. Finishing video.", flush=True)
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stitch video scenes.")
    parser.add_argument("--image", required=True, help="Path to image")
    parser.add_argument("--audio", required=True, help="Path to audio")
    parser.add_argument("--output", default="output.mp4", help="Output video path")
    
    args = parser.parse_args()
    engine = VideoEngine()
    engine.create_scene_clip(args.image, args.audio, args.output)
