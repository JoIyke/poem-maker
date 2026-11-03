import argparse
import os
import subprocess
from faster_whisper import WhisperModel

# Colors in BGR format for ASS Subtitles
SPEAKER_COLORS = [
    "&H0000FFFF&",  # Yellow
    "&H00FFFF00&",  # Cyan / Aqua
    "&H0000FF66&",  # Neon Green
    "&H00FF66FF&",  # Magenta / Pink
    "&H0000A5FF&",  # Vibrant Orange
    "&H00FFFFFF&"   # White
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

    def _get_speaker_for_time(self, timestamp, scene_timeline):
        """Looks up which speaker is active at this exact second."""
        for item in scene_timeline:
            if item["start"] <= timestamp <= item["end"]:
                return item["speaker"]
        return scene_timeline[-1]["speaker"] if scene_timeline else "Speaker"

    def generate_animated_ass(self, video_path, ass_path, scene_timeline, width=1080, height=1920):
        print(f"Transcribing {video_path} for speaker-aware captions...", flush=True)
        segments, _ = self.model.transcribe(video_path, word_timestamps=True)

        fontsize = 64 if width < height else 48
        margin_v = int(height * 0.28) if width < height else int(height * 0.15)

        # Build mapping of unique speakers to colors
        unique_speakers = list(dict.fromkeys([s["speaker"] for s in scene_timeline]))
        speaker_color_map = {spk: SPEAKER_COLORS[idx % len(SPEAKER_COLORS)] for idx, spk in enumerate(unique_speakers)}

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

                    # Identify speaker and their assigned color
                    current_speaker = self._get_speaker_for_time(active_word.start, scene_timeline)
                    highlight_color = speaker_color_map.get(current_speaker, "&H0000FFFF&")

                    # Speaker label badge: e.g. 🎙️ JOSHUA:
                    badge = f"{{\\c{highlight_color}\\b1\\fs{int(fontsize * 0.65)}}}🎙️ {current_speaker.upper()}:\\N{{\\r\\fs{fontsize}}}"

                    line_pieces = []
                    for idx, w in enumerate(chunk):
                        word_text = w.word.strip().upper()
                        if idx == current_idx:
                            # Highlighted active word
                            line_pieces.append(f"{{\\c{highlight_color}\\b1}}{word_text}{{\\r}}")
                        else:
                            line_pieces.append(word_text)

                    dialogue_text = badge + " ".join(line_pieces)
                    ass_content.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{dialogue_text}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write("\n".join(ass_content))

    def burn_captions(self, input_video, output_video, scene_timeline, width=1080, height=1920):
        ass_path = input_video.replace(".mp4", "_captions.ass")
        self.generate_animated_ass(input_video, ass_path, scene_timeline, width, height)

        print(f"Burning speaker-aware captions onto {output_video}...", flush=True)
        cmd = [
            "ffmpeg", "-nostdin", "-y", "-i", input_video,
            "-vf", f"ass={ass_path}:fontsdir=workspace",
            "-c:a", "copy", output_video
        ]
        subprocess.run(cmd)

        if os.path.exists(ass_path):
            os.remove(ass_path)
            
        return output_video
