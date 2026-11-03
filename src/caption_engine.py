import argparse
import os
import subprocess
from faster_whisper import WhisperModel

class CaptionEngine:
    def __init__(self, model_size="base.en"):
        print(f"Loading Whisper model ({model_size}) on CPU...", flush=True)
        # int8 compute type is super-fast on standard CPUs
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def _format_timestamp(self, seconds):
        """Converts seconds into ASS subtitle format: H:MM:SS.cs"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centis = int((secs - int(secs)) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centis:02d}"

    def generate_animated_ass(self, video_path, ass_path, width=1080, height=1920):
        """Transcribes video and generates an ASS file with word-by-word highlights."""
        print(f"Transcribing {video_path} for word-level captions...", flush=True)
        segments, _ = self.model.transcribe(video_path, word_timestamps=True)

        fontsize = 72 if width < height else 52
        margin_v = int(height * 0.32) if width < height else int(height * 0.15)

        # ASS header with bold font and custom styling
        # Primary color: White (&H00FFFFFF), Highlight color: Yellow (&H0000FFFF)
        ass_content = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,Roboto-Bold,{fontsize},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,40,40,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        # Process words into short punchy groups (3 to 4 words per line)
        for segment in segments:
            words = [w for w in segment.words]
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue

                # For every word in this group, create a frame where that word is highlighted
                for current_idx, active_word in enumerate(chunk):
                    start_str = self._format_timestamp(active_word.start)
                    end_str = self._format_timestamp(active_word.end)

                    line_pieces = []
                    for idx, w in enumerate(chunk):
                        word_text = w.word.strip().upper()
                        if idx == current_idx:
                            # Highlighted active word in Bright Yellow (&H0000FFFF&)
                            line_pieces.append(f"{{\\c&H0000FFFF&}}{word_text}{{\\r}}")
                        else:
                            line_pieces.append(word_text)

                    dialogue_text = " ".join(line_pieces)
                    ass_content.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_content))
        print(f"Generated ASS subtitle file: {ass_path}", flush=True)

    def burn_captions(self, input_video, output_video, width=1080, height=1920):
        """Burns the animated ASS captions onto the final video."""
        ass_path = input_video.replace(".mp4", "_captions.ass")
        self.generate_animated_ass(input_video, ass_path, width, height)

        print(f"Burning animated captions onto {output_video}...", flush=True)
        # fontsdir points to workspace where font.ttf resides
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-i", input_video,
            "-vf", f"ass={ass_path}:fontsdir=workspace",
            "-c:v", "libx264", "-c:a", "copy", output_video
        ]
        subprocess.run(cmd)

        if os.path.exists(ass_path):
            os.remove(ass_path)
            
        print(f"Animated captioned video ready: {output_video}", flush=True)
        return output_video

# CLI Interface: Allows you to trigger ONLY captioning from GitHub Actions later!
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add animated captions to a video.")
    parser.add_argument("--input", required=True, help="Input video file path")
    parser.add_argument("--output", default="captioned_output.mp4", help="Output video file path")
    parser.add_argument("--width", type=int, default=1080, help="Video width")
    parser.add_argument("--height", type=int, default=1920, help="Video height")

    args = parser.parse_args()
    engine = CaptionEngine()
    engine.burn_captions(args.input, args.output, args.width, args.height)
