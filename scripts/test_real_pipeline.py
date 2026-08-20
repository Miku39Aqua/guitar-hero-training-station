"""测试 basic-pitch 真实音频输入 → MIDI → ScoreIR"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import librosa
import soundfile as sf

from audio.basic_pitch_runner import detect_pitch
from audio.fret_engine import midi_notes_to_ir
from tab_engine.to_alphatex import score_to_alphatex_compact

# 1. 生成测试音频：简单旋律（C4-G4-A4-G4 旋律）
sr = 44100
duration = 2.0
freqs = [261.63, 392.00, 440.00, 392.00]  # C4, G4, A4, G4
note_dur = duration / len(freqs)

t = np.linspace(0, note_dur, int(sr * note_dur), False)
audio = np.concatenate([0.3 * np.sin(2 * np.pi * f * t) for f in freqs])

# 保存
test_wav = Path("output/test_basic_pitch.wav")
sf.write(test_wav, audio, sr)
print(f"已生成测试音频: {test_wav} ({len(audio)/sr:.1f}s)")

# 2. basic-pitch 音高检测
print("\n=== basic-pitch 音高检测 ===")
notes = detect_pitch(str(test_wav))
print(f"检测到 {len(notes)} 个音符:")
for n in notes[:10]:
    print(f"  start={n['start']:.3f}s  pitch={n['pitch']}  dur={n['duration']:.3f}s")

# 3. MIDI → ScoreIR → alphaTex
print("\n=== 生成 alphaTex ===")
ir = midi_notes_to_ir(notes, bpm=120)
print(f"IR 小节数: {len(ir.measures)}")

alphatex = score_to_alphatex_compact(ir)
print(f"alphaTex ({len(alphatex)} 字符):")
print(alphatex[:300])

# 写文件
Path("output/test_real_pipeline.alphatex.txt").write_text(alphatex, encoding="utf-8")
print("\n已写入 output/test_real_pipeline.alphatex.txt")
