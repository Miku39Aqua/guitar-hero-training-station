"""音频管线：音频 → ScoreIR

Stage 1: Demucs 分离吉他音轨
Stage 2: basic-pitch 音高检测（MIDI/音符）
Stage 3: 指法引擎（DP）生成六线谱 ScoreIR
"""
from pathlib import Path

from tab_engine.ir import ScoreIR
from .demucs_runner import separate_guitar
from .basic_pitch_runner import detect_pitch
from .fret_engine import midi_notes_to_ir
from .bpm_detector import estimate_bpm


def transcribe_audio(audio_path: str, mode: str = "song", progress_callback=None) -> ScoreIR:
    """主入口：音频文件 → ScoreIR

    Args:
        audio_path: 音频文件路径（wav/mp3/flac 等）
        mode: "song"（完整歌曲，自动分离吉他）或 "guitar"（已是吉他音轨，直接检测）
        progress_callback: 可选，回调函数 (stage, message)

    Returns:
        ScoreIR 对象
    """
    audio_path = str(audio_path)
    title = Path(audio_path).stem

    # 先用原曲识别 BPM（鼓点更准确），后续转谱强制使用这个 BPM
    if progress_callback:
        progress_callback("正在识别歌曲速度...")
    bpm = estimate_bpm(audio_path)

    if mode == "guitar":
        # 已是吉他音轨，跳过 Demucs
        if progress_callback:
            progress_callback("正在进行音高检测...")
        midi_notes = detect_pitch(audio_path)
    else:
        # 默认：完整歌曲，先分离
        if progress_callback:
            progress_callback("正在分离吉他音轨...")
        guitar_wav = separate_guitar(audio_path)
        if progress_callback:
            progress_callback("正在进行音高检测...")
        midi_notes = detect_pitch(guitar_wav)

    if progress_callback:
        progress_callback("正在生成六线谱...")

    # Stage 3: MIDI → ScoreIR，使用识别到的 BPM
    ir = midi_notes_to_ir(midi_notes, title=title, bpm=bpm)

    return ir
