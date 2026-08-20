"""Stage 2: 使用 basic-pitch 对吉他音轨进行音高检测（最小可运行版）"""
import os


def detect_pitch(guitar_wav_path: str) -> list[dict]:
    """对吉他音轨进行音高检测，返回音符列表。

    Args:
        guitar_wav_path: Demucs 分离出的吉他音轨 wav 路径

    Returns:
        [
            {"start": 0.0, "pitch": 60, "duration": 0.5},
            ...
        ]
        pitch 为 MIDI 音高（60 = Middle C）
    """
    try:
        import numpy as np
        from basic_pitch.inference import predict
        from basic_pitch import ICASSP_2022_MODEL_PATH
        import librosa

        # basic-pitch predict 返回 (raw_output, pretty_midi, note_events)
        # raw_output[0] 是 dict {"note": ..., "onset": ..., "contour": ...}
        # note_events: list of tuples (start_time, end_time, pitch, confidence, ...)
        model_output = predict(guitar_wav_path, model_or_model_path=ICASSP_2022_MODEL_PATH)
        notes = model_output[2]  # note_events 列表

        result = []
        for note in notes:
            # note 是 tuple: (start, end, pitch, confidence, ...)
            if len(note) >= 3:
                result.append({
                    "start": float(note[0]),
                    "pitch": int(note[2]),
                    "duration": float(note[1] - note[0]),
                })
        return result

    except Exception as e:
        print(f"[basic-pitch] 检测失败: {e}")
        return []
