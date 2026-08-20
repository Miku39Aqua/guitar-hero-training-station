"""改编引擎测试：三条规则（横按规避/把位收敛/快速降级）各构造一个用例

运行: python scripts/step1_adapt_test.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR
from tab_engine.adapt import adapt_difficulty


def build_hard_score() -> ScoreIR:
    ir = ScoreIR(title="难度测试谱", bpm=140)

    # 小节1: F 大横按和弦 (133211) → 触发横按规避
    f_barre = [NoteIR(string=6, fret=1), NoteIR(string=5, fret=3),
               NoteIR(string=4, fret=3), NoteIR(string=3, fret=2),
               NoteIR(string=2, fret=1), NoteIR(string=1, fret=1)]
    m1 = MeasureIR(beats=[
        BeatIR(duration=4, notes=f_barre),
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=0)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=3)]),
        BeatIR(duration=4),
    ])
    ir.measures.append(m1)

    # 小节2: 低音弦高把位音（5弦17品, 音高62）→ 触发把位收敛（应换到4弦12品, 音高不变）
    m2 = MeasureIR(beats=[
        BeatIR(duration=4, notes=[NoteIR(string=5, fret=17)]),
        BeatIR(duration=4, notes=[NoteIR(string=1, fret=12)]),
        BeatIR(duration=2),
    ])
    ir.measures.append(m2)

    # 小节3: 四个16分音符跑动 → 触发快速降级（max_note_duration=8）
    run = [BeatIR(duration=16, notes=[NoteIR(string=3, fret=2)]),
           BeatIR(duration=16, notes=[NoteIR(string=3, fret=4)]),
           BeatIR(duration=16, notes=[NoteIR(string=3, fret=5)]),
           BeatIR(duration=16, notes=[NoteIR(string=3, fret=7)])]
    m3 = MeasureIR(beats=run + [BeatIR(duration=2)])
    ir.measures.append(m3)

    return ir


def fmt(ir: ScoreIR) -> str:
    lines = []
    for i, m in enumerate(ir.measures, 1):
        parts = []
        for b in m.beats:
            notes = "+".join(f"{n.string}s{n.fret}f" for n in b.notes) or "rest"
            parts.append(f"[1/{b.duration} {notes}]")
        lines.append(f"  小节{i}: " + " ".join(parts))
    return "\n".join(lines)


def main():
    original = build_hard_score()
    profile = {"no_barre": True, "max_fret": 12, "max_note_duration": 8,
               "level": "中级", "tone_pref": "轻过载"}

    adapted, report = adapt_difficulty(original, profile)

    print("=== 原谱 ===")
    print(fmt(original))
    print("\n=== 改编后（画像: 横按困难/把位<=12/最快1/8）===")
    print(fmt(adapted))
    print("\n=== 改编报告（Agent 将引用此文本）===")
    print(report.summary_text())

    # ---- 断言 ----
    # 规则1: 横按6音 → 2音
    assert len(adapted.measures[0].beats[0].notes) == 2, "横按应简化为双音"
    # 规则2: 5弦17品(音高62) → 应换到其他弦 <=12品
    n = adapted.measures[1].beats[0].notes[0]
    assert n.fret <= 12, f"把位应<=12品, 实际{n.string}弦{n.fret}品"
    # 音高守恒: 5弦(A=45)17品 = 62
    tuning = original.tuning
    assert tuning[n.string - 1] + n.fret == 45 + 17, "换弦后音高必须不变"
    # 规则3: 4个16分 → 2个8分 + 2个8分休止（总时值守恒）
    m3 = adapted.measures[2]
    assert [b.duration for b in m3.beats] == [8, 8, 8, 8, 2], "16分应合并为8分"
    assert len(m3.beats[0].notes) == 1 and len(m3.beats[1].notes) == 0
    assert len(m3.beats[2].notes) == 1 and len(m3.beats[3].notes) == 0
    # 原 IR 不被修改
    assert len(original.measures[0].beats[0].notes) == 6, "原谱不应被修改"

    print("\nOK: 三条改编规则全部生效，断言通过")


if __name__ == "__main__":
    main()
