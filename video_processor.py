"""
视频处理模块：提取音频 -> Whisper 识别 -> 生成中英双字幕 VTT
"""
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    """懒加载 faster-whisper 模型（base 模型，平衡速度与精度）"""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info("Loading Whisper base model...")
        _model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("Whisper model loaded.")
    return _model


def format_vtt_time(seconds: float) -> str:
    """秒数转 WebVTT 时间格式 HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def segments_to_vtt(segments_list: list, output_path: str):
    """将字幕片段列表写成 WebVTT 文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, seg in enumerate(segments_list):
            start = format_vtt_time(seg["start"])
            end = format_vtt_time(seg["end"])
            text = seg["text"].strip()
            if not text:
                continue
            f.write(f"{i + 1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{text}\n\n")


def extract_audio(video_path: str, audio_path: str):
    """用 ffmpeg 从视频提取 16kHz 单声道 wav"""
    result = subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y", audio_path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-500:]}")


def process_video_subtitles(video_id: int, video_path: str, subtitle_dir: str) -> dict:
    """
    处理视频：提取音频 -> 转录原文 -> 翻译英文 -> 生成 VTT
    返回 {"orig_vtt": path, "en_vtt": path, "detected_language": str, "duration": float}
    """
    os.makedirs(subtitle_dir, exist_ok=True)
    audio_path = os.path.join(subtitle_dir, f"{video_id}_audio.wav")
    orig_vtt = os.path.join(subtitle_dir, f"{video_id}_orig.vtt")
    en_vtt = os.path.join(subtitle_dir, f"{video_id}_en.vtt")

    try:
        logger.info(f"[Video {video_id}] Extracting audio...")
        extract_audio(video_path, audio_path)

        model = get_whisper_model()

        # 转录原始语言
        logger.info(f"[Video {video_id}] Transcribing original language...")
        orig_segments_gen, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        orig_list = [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in orig_segments_gen
        ]
        segments_to_vtt(orig_list, orig_vtt)
        logger.info(f"[Video {video_id}] Original subtitles saved ({len(orig_list)} segments, lang={info.language})")

        # 翻译为英文
        logger.info(f"[Video {video_id}] Translating to English...")
        en_segments_gen, _ = model.transcribe(
            audio_path,
            beam_size=5,
            task="translate",
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        en_list = [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in en_segments_gen
        ]
        segments_to_vtt(en_list, en_vtt)
        logger.info(f"[Video {video_id}] English subtitles saved ({len(en_list)} segments)")

        return {
            "orig_vtt": orig_vtt,
            "en_vtt": en_vtt,
            "detected_language": info.language,
            "duration": getattr(info, "duration", 0) or 0,
        }
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
