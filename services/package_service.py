"""分轨打包服务：将选中的轨道打包成 zip。"""
import zipfile
from pathlib import Path


def package_stems(
    zip_path: Path,
    stem_paths: dict[str, Path],
    original_name: str,
) -> int:
    """将轨道文件打包为 zip，返回 zip 文件大小（字节）。

    Args:
        zip_path: 输出 zip 路径
        stem_paths: {label: wav_path}，如 {"guitar": ..., "no_guitar": ...}
        original_name: 原曲名，用于 zip 内文件名
    """
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for label, wav_path in stem_paths.items():
            arcname = f"{original_name} - {label}.wav"
            zf.write(str(wav_path), arcname)
    return zip_path.stat().st_size
