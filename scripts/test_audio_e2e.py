"""端到端测试：模拟真实音频输入，验证整个管线能出 alphaTex"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from audio.fret_engine import midi_notes_to_ir
from tab_engine.to_alphatex import score_to_alphatex_compact

# 模拟一个简单的吉他 riff（类似 "Smoke on the Water" 开头）
midi_notes = [
    {"start": 0.0,  "pitch": 55, "duration": 0.5},  # G2 (3弦空弦)
    {"start": 0.5,  "pitch": 58, "duration": 0.5},  # A#2 (3弦3品)
    {"start": 1.0,  "pitch": 60, "duration": 0.25}, # C3 (2弦1品)
    {"start": 1.25, "pitch": 55, "duration": 0.5},  # G2
    {"start": 1.75, "pitch": 58, "duration": 0.5},  # A#2
    {"start": 2.25, "pitch": 60, "duration": 0.25}, # C3
    {"start": 2.5,  "pitch": 63, "duration": 0.5},  # D#3 (3弦5品)
    {"start": 3.0,  "pitch": 63, "duration": 1.0},  # D#3
]

print("=== MIDI 输入 ===")
for n in midi_notes:
    print(f"  {n['start']:.2f}s  pitch={n['pitch']}  dur={n['duration']:.2f}s")

ir = midi_notes_to_ir(midi_notes, bpm=120)

print(f"\n=== IR 结构 ===")
print(f"标题: {ir.title}")
print(f"小节数: {len(ir.measures)}")
for i, m in enumerate(ir.measures):
    print(f"  小节 {i+1}:")
    for j, b in enumerate(m.beats):
        if b.notes:
            for n in b.notes:
                print(f"    拍 {j+1}: 弦{n.string}品{n.fret} 时值{b.duration}")

alphatex = score_to_alphatex_compact(ir)
print(f"\n=== alphaTex ({len(alphatex)} 字符) ===")
print(alphatex[:400])

# 写文件
Path("output/test_audio_pipeline.alphatex.txt").write_text(alphatex, encoding="utf-8")
print("\n已写入 output/test_audio_pipeline.alphatex.txt")
