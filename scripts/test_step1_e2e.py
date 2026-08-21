"""Step 1 端到端验证：音频 → Demucs → basic-pitch → ScoreIR → alphaTex"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from audio.demucs_runner import separate_guitar
from audio.basic_pitch_runner import detect_pitch
from audio.fret_engine import midi_notes_to_ir
from tab_engine.to_alphatex import score_to_alphatex_compact

AUDIO_PATH = Path("uploads") / "影色舞.MP3"
OUTPUT_DIR = Path("uploads") / "demucs_output"


def main():
    if not AUDIO_PATH.exists():
        print(f"测试音频不存在: {AUDIO_PATH}")
        raise SystemExit(1)

    print(f"1/4 音频分离: {AUDIO_PATH}")
    guitar_wav = separate_guitar(str(AUDIO_PATH), output_dir=str(OUTPUT_DIR), model="htdemucs_6s")
    print(f"   吉他音轨: {guitar_wav}")

    print("2/4 音高检测")
    notes = detect_pitch(guitar_wav)
    print(f"   检测到 {len(notes)} 个音符")

    print("3/4 生成 ScoreIR")
    ir = midi_notes_to_ir(notes, bpm=120)
    print(f"   小节数: {len(ir.measures)}")

    print("4/4 转 alphaTex")
    alphatex = score_to_alphatex_compact(ir)
    print(f"   长度: {len(alphatex)} 字符")
    print("\n=== alphaTex 预览 ===")
    print(alphatex[:800])


if __name__ == "__main__":
    main()
