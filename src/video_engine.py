import argparse
import subprocess
import os

class VideoEngine:
    def __init__(self):
        # We assume FFmpeg is installed on the system (GitHub Actions comes with it pre-installed)
        pass

    def create_scene_clip(self, image_path, audio_path, output_path):
        """
        Combines a single image and a single audio file into a video clip.
        The video length will exactly match the audio length.
        """
        print(f"Creating scene clip: {output_path}")
        
        # FFmpeg command:
        # -loop 1: Loop the single image
        # -i: Inputs (Image and Audio)
        # -c:v libx264: Standard video codec
        # -tune stillimage: Optimizes encoding for a static image
        # -c:a aac: Standard audio codec
        # -b:a 192k: Audio bitrate
        # -pix_fmt yuv420p: Ensures compatibility with all media players
        # -shortest: Cuts the video exactly when the audio ends
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
            "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-shortest", output_path
        ]
        
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path

    def concatenate_clips(self, clip_paths, final_output_path, bgm_path=None):
        """
        Stitches multiple scene clips together and optionally adds background music.
        """
        print("Concatenating scenes together...")
        
        # Create a text file listing all clips for FFmpeg's concat demuxer
        list_file = "clips_list.txt"
        with open(list_file, "w") as f:
            for clip in clip_paths:
                f.write(f"file '{clip}'\n")

        temp_output = "temp_merged.mp4"
        
        concat_cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", 
            "-i", list_file, "-c", "copy", temp_output
        ]
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not bgm_path or not os.path.exists(bgm_path):
            print("No BGM provided or found. Finishing video.")
            os.rename(temp_output, final_output_path)
        else:
            print("Adding background music...")
            # Mix the scene audio (narration) with the background music
            # Volume control: Narration stays at 1.0, BGM lowered to 0.1
            bgm_cmd = [
                "ffmpeg", "-y", "-i", temp_output, "-stream_loop", "-1", "-i", bgm_path,
                "-filter_complex", "[0:a]volume=1.0[a1];[1:a]volume=0.1[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:v", "copy", "-c:a", "aac", final_output_path
            ]
            subprocess.run(bgm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(temp_output)
            
        os.remove(list_file)
        print(f"Final video saved to {final_output_path}")
        return final_output_path

# CLI capabilities for standalone use
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stitch video scenes.")
    parser.add_argument("--image", required=True, help="Path to image")
    parser.add_argument("--audio", required=True, help="Path to audio")
    parser.add_argument("--output", default="output.mp4", help="Output video path")
    
    args = parser.parse_args()
    engine = VideoEngine()
    engine.create_scene_clip(args.image, args.audio, args.output)
