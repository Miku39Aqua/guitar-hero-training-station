"""Stage 1: 使用 Demucs 从混音中分离吉他音轨（最小可运行版）"""
import os
from pathlib import Path


def separate_guitar(audio_path: str, output_dir: str | None = None) -> str:
    """使用 Demucs 分离音轨，返回吉他音轨文件路径。

    最小可运行版：如果 Demucs 未就绪，直接返回原文件作为 fallback。
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    if output_dir is None:
        output_dir = audio_path.parent / "demucs_output"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        from demucs.separate import main as demucs_main
        import torch

        class Args:
            pass

        args = Args()
        args.tracks = [str(audio_path)]
        args.out = str(output_dir)
        args.model = "htdemucs"
        args.device = "cuda" if torch.cuda.is_available() else "cpu"
        args.shifts = 5
        args.shift = True
        args.jobs = 1
        args.mp = False
        args.float16 = True
        args.samplerate = 44100
        args.split_mode = "standard"
        args.two_stems = "other"
        args.margin = 44100
        args.duration = None
        args.fragment = "6"
        args.overlap = 0.25
        args.mp3 = False
        args.mp3_bitrate = 320
        args.stem_only = True
        args.multi_stem = None
        args.verbose = False

        demucs_main(args)

        stem_name = audio_path.stem
        guitar_path = output_dir / args.model / stem_name / "other.wav"
        if not guitar_path.exists():
            wavs = list((output_dir / args.model / stem_name).glob("*.wav"))
            if wavs:
                guitar_path = wavs[0]
            else:
                raise FileNotFoundError(f"Demucs 输出未找到: {output_dir / args.model / stem_name}")

        return str(guitar_path)

    except Exception as e:
        print(f"[demucs] 分离失败，使用原文件 fallback: {e}")
        return str(audio_path)
