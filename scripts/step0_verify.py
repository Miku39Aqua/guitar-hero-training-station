"""Step 0 验证：IR → 导出 .gp5 → 读回校验（roundtrip）

运行: python scripts/step0_verify.py
通过标准: 无断言错误，且生成的 output/step0_test.gp5 能用 Guitar Pro 正常打开
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tab_engine import ScoreIR, MeasureIR, BeatIR, NoteIR, import_gp, export_gp

OUT = os.path.join(os.path.dirname(__file__), "..", "output", "step0_test.gp5")

# 开放把位 C 大调音阶: (弦, 品)
C_SCALE = [(5, 3), (4, 0), (4, 2), (4, 3), (3, 0), (3, 2), (2, 0), (2, 1)]


def build_score() -> ScoreIR:
    ir = ScoreIR(title="Step0 Test - C Major Scale", artist="guitar-hero-training-station", bpm=120)

    # 小节1: 音阶上行（八分音符）
    m1 = MeasureIR()
    for string, fret in C_SCALE:
        m1.beats.append(BeatIR(duration=8, notes=[NoteIR(string=string, fret=fret)]))
    ir.measures.append(m1)

    # 小节2: 音阶下行
    m2 = MeasureIR()
    for string, fret in reversed(C_SCALE):
        m2.beats.append(BeatIR(duration=8, notes=[NoteIR(string=string, fret=fret)]))
    ir.measures.append(m2)

    # 小节3: C 和弦(同时多音) + 四分音符单音 + 休止
    c_chord = [NoteIR(string=5, fret=3), NoteIR(string=4, fret=2),
               NoteIR(string=3, fret=0), NoteIR(string=2, fret=1)]
    m3 = MeasureIR(beats=[
        BeatIR(duration=4, notes=c_chord),
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=2)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=0)]),
        BeatIR(duration=4),  # 四分休止
    ])
    ir.measures.append(m3)

    return ir


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    original = build_score()
    export_gp(original, OUT)
    print(f"[1/2] 已导出: {os.path.abspath(OUT)}")

    back = import_gp(OUT)
    print(f"[2/2] 已读回: title={back.title!r} bpm={back.bpm} "
          f"time_sig={back.time_sig} measures={len(back.measures)}")

    assert back.bpm == original.bpm, "BPM 不一致"
    assert back.time_sig == original.time_sig, f"拍号不一致: {back.time_sig}"
    assert len(back.measures) == len(original.measures), "小节数不一致"

    for i, (m_orig, m_back) in enumerate(zip(original.measures, back.measures)):
        # 和弦内音符顺序在 gp 格式中不保留（同拍同时发声，顺序无语义），按 beat 内集合比较
        assert len(m_orig.beats) == len(m_back.beats), f"小节{i+1}拍数不一致"
        for j, (b_orig, b_back) in enumerate(zip(m_orig.beats, m_back.beats)):
            s_orig = sorted((n.string, n.fret) for n in b_orig.notes)
            s_back = sorted((n.string, n.fret) for n in b_back.notes)
            assert s_orig == s_back, f"小节{i+1}拍{j+1}音符不一致: {s_orig} vs {s_back}"

    print("OK: roundtrip 校验全部通过")
    print(">>> 请用 Guitar Pro 打开 output/step0_test.gp5 做最终人工验收 <<<")


if __name__ == "__main__":
    main()
