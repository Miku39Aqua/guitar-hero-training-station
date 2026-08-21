"""Step 1 依赖就绪验证：安装依赖并触发 Demucs htdemucs_6s 模型下载"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio.demucs_runner import separate_guitar

# 先检查上传目录里的样例音频
uploads = Path("uploads")
mp3s = sorted(uploads.glob("*.mp3")) + sorted(uploads.glob("*.MP3")) + sorted(uploads.glob("*.wav"))
if not mp3s:
    print("未找到音频文件，请先往 uploads/ 放一首歌，再运行此脚本。")
    raise SystemExit(1)

sample = str(mp3s[0])
print(f"测试音频: {sample}")
print("开始调用 Demucs（首次会自动下载模型，约 1.8GB，请耐心等待）...")
out = separate_guitar(sample, model="htdemucs_6s")
print(f"分离完成: {out}")
if Path(out).exists():
    print(f"输出大小: {Path(out).stat().st_size / 1024 / 1024:.1f} MB")
else:
    print("输出文件不存在")
