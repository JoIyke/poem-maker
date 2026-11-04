import argparse
import os
import subprocess
from faster_whisper import WhisperModel

# High-contrast vibrant colors in BGR format for ASS Subtitles
SPEAKER_COLORS = [
    "&H0000FFFF&",  # Electric Yellow
    "&H00FFFF00&",  # Cyan / Aqua
    "&H0000FF66&",  # Neon Green
    "&H00FF88FF&",  # Soft Pink
    "&H0000A5FF&",  # Orange
    "&H00FFFFFF&"   # Crisp White
]

class CaptionEngine:
    def __init__(self, model_size="base.en"):
        print(f"Loading Whisper model ({model_size}) on CPU...", flush=True)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def _format_timestamp(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        centis = int((secs - int(secs)) * 100)
        return f"{hours}:{minutes:02d}:{int(secs):02d}.{centis:02d}"

    def _get_speaker_info(self, timestamp, scene_timeline, unique_speakers):
        """Finds who is speaking and returns their index (for left/right alignment and color)."""
        speaker_name = unique_speakers[0] if unique_speakers else "Speaker"
        for item in scene_timeline:
            if item["start"] <= timestamp <= item["end"]:
                speaker_name = item["speaker"]
                break

        try:
            spk_idx = unique_speakers.index(speaker_name)
        except ValueError:
            spk_idx = 0

        color = SPEAKER_COLORS[spk_idx % len(SPEAKER_COLORS)]
        # Speaker 0 (1st) on Left, Speaker 1 (2nd) on Right, Speaker 2 (3rd) on Left, etc.
        style = "BubbleLeft" if (spk_idx % 2 == 0) else "BubbleRight"
        return speaker_name, spk_idx, color, style

    def generate_dialogue_ass(self, video_path, ass_path, scene_timeline, width=1080, height=1920):
        """
        Creates sentence-level speech/comment bubbles in corners for multiple speakers.
        No emojis, no speaker names, opaque dark bubble background.
        """
        print(f"Generating Multi-Speaker Dialogue Bubbles for {video_path}...", flush=True)
        segments, _ = self.model.transcribe(video_path, word_timestamps=False)

        fontsize = 46 if width < height else 38
        margin_v = int(height * 0.22) if width < height else int(height * 0.12)
        unique_speakers = list(dict.fromkeys([s["speaker"] for s in scene_timeline]))

        # BorderStyle: 3 creates an opaque comment bubble behind the text
        # Outline: 10 acts as padding for the bubble
        # OutlineColour: &HCC161616& is an 80% opaque dark charcoal bubble
        ass_content = [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            # Speaker 1: Lower-Left Corner (Alignment 1), constrained to left side
            f"Style: BubbleLeft,Roboto-Bold,{fontsize},&H00FFFFFF,&H000000FF,&HCC161616,&H00000000,-1,0,0,0,100,100,0,0,3,10,0,1,60,340,{margin_v},1",
            # Speaker 2: Lower-Right Corner (Alignment 3), constrained to right side
            f"Style: BubbleRight,Roboto-Bold,{fontsize},&H00FFFFFF,&H000000FF,&HCC161616,&H00000000,-1,0,0,0,100,100,0,0,3,10,0,3,340,60,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        for segment in segments:
            clean_text = segment.text.strip()
            if not clean_text:
                continue

            mid_point = (segment.start + segment.end) / 2
            _, _, color, style_name = self._get_speaker_info(mid_point, scene_timeline, unique_speakers)

            start_str = self._format_timestamp(segment.start)
            end_str = self._format_timestamp(segment.end)

            # Renders full phrase in the speaker's assigned color inside their corner bubble
            dialogue = f"{{\\c{color}}}{clean_text}"
            ass_content.append(f"Dialogue: 0,{start_str},{end_str},{style_name},,0,0,0,,{dialogue}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_content))

    def generate_animated_ass(self, video_path, ass_path, width=1080, height=1920):
        """
        Restored clean single-speaker animated captions (Hormozi style).
        Centered, 3-4 words, active word highlighted in bright yellow, zero emojis.
        """
        print(f"Generating Clean Animated Captions for {video_path}...", flush=True)
        segments, _ = self.model.transcribe(video_path, word_timestamps=True)

        fontsize = 68 if width < height else 50
        margin_v = int(height * 0.28) if width < height else int(height * 0.15)

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

        for segment in segments:
            words = [w for w in segment.words]
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                chunk = words[i:i + chunk_size]
                if not chunk:
                    continue

                for current_idx, active_word in enumerate(chunk):
                    start_str = self._format_timestamp(active_word.start)
                    end_str = self._format_timestamp(active_word.end)

                    line_pieces = []
                    for idx, w in enumerate(chunk):
                        word_text = w.word.strip().upper()
                        if idx == current_idx:
                            # Highlight active word in Bright Yellow (&H0000FFFF&)
                            line_pieces.append(f"{{\\c&H0000FFFF&\\b1}}{word_text}{{\\r}}")
                        else:
                            line_pieces.append(word_text)

                    dialogue_text = " ".join(line_pieces)
                    ass_content.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_content))

    def burn_captions(self, input_video, output_video, scene_timeline=None, mode="dialogue", width=1080, height=1920):
        ass_path = input_video.replace(".mp4", "_captions.ass")

        if mode == "dialogue":
            self.generate_dialogue_ass(input_video, ass_path, scene_timeline or [], width, height)
        else:
            self.generate_animated_ass(input_video, ass_path, width, height)

        print(f"Burning captions ({mode}) onto {output_video}...", flush=True)
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-i", input_video,
            "-vf", f"ass={ass_path}:fontsdir=workspace",
            "-c:a", "copy", output_video
        ]
        subprocess.run(cmd)

        if os.path.exists(ass_path):
            os.remove(ass_path)
            
        print(f"Captioned video ready: {output_video}", flush=True)
        return output_video
