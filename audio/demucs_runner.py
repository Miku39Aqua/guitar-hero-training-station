"""Stage 1: 使用 Demucs 从混音中分离音轨。"""
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf


ALL_HT_DEMACS_STEMS = ["vocals", "drums", "bass", "guitar", "piano", "other"]


def separate_guitar(audio_path: str, output_dir: str | None = None, model: str = "htdemucs_6s") -> str:
    """兼容旧接口：只分离吉他/其他两轨，返回吉他音轨路径。"""
    stems = separate_stems(audio_path, output_dir=output_dir, model=model, selected_stems=["guitar"])
    return str(stems["guitar"])


def separate_stems(
    audio_path: str,
    output_dir: str | None = None,
    model: str = "htdemucs_6s",
    selected_stems: list[str] | None = None,
) -> dict[str, Path]:
    """使用 Demucs 分离全部 6 轨，并生成每个选中 stem 的排除轨道。

    Args:
        audio_path: 输入音频路径
        output_dir: Demucs 输出目录，默认 uploads/demucs_output
        model: Demucs 模型，默认 htdemucs_6s
        selected_stems: 用户选择的轨道列表，如 ["guitar", "piano"]

    Returns:
        字典，包含每个选中轨道及其排除轨道：
        {
            "guitar": Path(.../guitar.wav),
            "piano": Path(.../piano.wav),
            "no_guitar": Path(.../no_guitar.wav),
            "no_piano": Path(.../no_piano.wav),
        }
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if output_dir is None:
        output_dir = audio_path.parent / "demucs_output"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem_name = audio_path.stem
    stem_dir = output_dir / model / stem_name

    # 如果还没分离过，运行 Demucs
    if not (stem_dir / "guitar.wav").exists():
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n", model,
            "-o", str(output_dir),
            str(audio_path),
        ]
        print(f"[demucs] 运行命令: {' '.join(cmd)}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    # 标记本次访问时间，供缓存清理按最近访问时间判断是否过期
    _touch_cache_dir(stem_dir)

    if selected_stems is None:
        selected_stems = ["guitar"]

    result: dict[str, Path] = {}
    for stem in selected_stems:
        if stem not in ALL_HT_DEMACS_STEMS:
            raise ValueError(f"不支持的轨道类型: {stem}")
        src = stem_dir / f"{stem}.wav"
        if not src.exists():
            raise FileNotFoundError(f"Demucs 未输出 {stem} 轨道: {src}")
        result[stem] = src

    # 为每个选中的 stem 生成排除轨道 no_<stem>.wav
    for stem in selected_stems:
        no_stem_path = stem_dir / f"no_{stem}.wav"
        if not no_stem_path.exists():
            remaining = [s for s in ALL_HT_DEMACS_STEMS if s != stem]
            _mix_stems(stem_dir, remaining, no_stem_path)
        result[f"no_{stem}"] = no_stem_path

    return result


def _mix_stems(stem_dir: Path, stems: list[str], out_path: Path):
    """将多个 stem 文件混合成一个文件，并做简单防削波。"""
    mix = None
    sr = None
    for s in stems:
        f = stem_dir / f"{s}.wav"
        if not f.exists():
            continue
        data, fs = sf.read(str(f))
        if sr is None:
            sr = fs
            mix = data.astype(np.float64)
        else:
            if data.shape != mix.shape:
                min_len = min(len(data), len(mix))
                data = data[:min_len]
                mix = mix[:min_len]
            mix = mix + data.astype(np.float64)

    if mix is None:
        raise FileNotFoundError(f"没有可用的轨道用于混合: {stem_dir}")

    peak = np.max(np.abs(mix))
    if peak > 1.0:
        mix = mix / peak

    sf.write(str(out_path), mix.astype(np.float32), sr)


def _touch_cache_dir(stem_dir: Path) -> None:
    """写一个 .last_access 标记文件，记录该缓存目录最近一次被访问的时间。"""
    try:
        (stem_dir / ".last_access").write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def cleanup_stale_cache(output_dir: str | Path, max_age_days: int = 7) -> list[str]:
    """清理超过 max_age_days 未被访问的 Demucs 缓存目录。

    通过每个曲目缓存目录下的 `.last_access` 标记文件判断最近访问时间；
    若标记文件不存在，则回退使用目录本身的修改时间。

    Args:
        output_dir: Demucs 输出根目录（如 uploads/demucs_output）
        max_age_days: 缓存最长保留天数，默认 7 天

    Returns:
        被删除的缓存目录路径列表
    """
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return []

    cutoff = time.time() - max_age_days * 86400
    removed: list[str] = []

    # 目录结构: output_dir/<model>/<stem_name>/
    for model_dir in output_dir.iterdir():
        if not model_dir.is_dir():
            continue
        for stem_dir in model_dir.iterdir():
            if not stem_dir.is_dir():
                continue
            marker = stem_dir / ".last_access"
            if marker.exists():
                try:
                    last_access = float(marker.read_text(encoding="utf-8").strip())
                except (OSError, ValueError):
                    last_access = stem_dir.stat().st_mtime
            else:
                last_access = stem_dir.stat().st_mtime

            if last_access < cutoff:
                shutil.rmtree(stem_dir, ignore_errors=True)
                removed.append(str(stem_dir))

    return removed
