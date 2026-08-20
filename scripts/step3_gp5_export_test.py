"""Step 3 测试：IR → gp5 导出

验证 ir_to_gp5 能正确生成 .gp5 文件，且能被 PyGuitarPro 读回。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR, STANDARD_TUNING
from tab_engine.to_gp5 import ir_to_gp5


def build_test_ir() -> ScoreIR:
    """构建一个包含 3 个小节的测试 ScoreIR"""
    ir = ScoreIR(
        title="gp5 导出测试",
        artist="GitHub Copilot",
        bpm=120,
        time_sig=(4, 4),
        tuning=STANDARD_TUNING.copy(),
    )

    # 小节 1：简单分解和弦（四分音符）
    m1 = MeasureIR()
    m1.beats.append(BeatIR(duration=4, notes=[NoteIR(string=1, fret=1)]))
    m1.beats.append(BeatIR(duration=4, notes=[NoteIR(string=2, fret=3)]))
    m1.beats.append(BeatIR(duration=4, notes=[NoteIR(string=3, fret=2)]))
    m1.beats.append(BeatIR(duration=4, notes=[]))  # 休止符
    ir.measures.append(m1)

    # 小节 2：八分音符
    m2 = MeasureIR()
    for _ in range(4):
        m2.beats.append(BeatIR(duration=8, notes=[NoteIR(string=5, fret=5)]))
    ir.measures.append(m2)

    # 小节 3：混合时值 + 和弦（多音）+ 休止符
    m3 = MeasureIR()
    m3.beats.append(BeatIR(duration=4, notes=[
        NoteIR(string=1, fret=0),
        NoteIR(string=2, fret=1),
        NoteIR(string=3, fret=2),
    ]))  # 三音和弦
    m3.beats.append(BeatIR(duration=8, notes=[NoteIR(string=4, fret=4)]))
    m3.beats.append(BeatIR(duration=8, notes=[NoteIR(string=5, fret=5)]))
    m3.beats.append(BeatIR(duration=4, notes=[]))  # 休止符
    ir.measures.append(m3)

    return ir


def main():
    output_path = str(Path(__file__).resolve().parent.parent / "output" / "step3_test.gp5")
    ir = build_test_ir()
    result = ir_to_gp5(ir, output_path)
    print(f"已生成: {result}")

    # 验证：用 PyGuitarPro 读回（需用 utf-8 解码，与写入时一致）
    import guitarpro
    song = guitarpro.parse(result, encoding='utf-8')
    print(f"标题: {song.title}")
    print(f"艺术家: {song.artist}")
    print(f"BPM: {song.tempo}")
    print(f"小节数: {len(song.tracks[0].measures)}")

    assert song.title == "gp5 导出测试", "标题不匹配"
    assert song.tempo == 120, "BPM 不匹配"
    assert len(song.tracks[0].measures) == 3, "小节数应为 3"

    print("Step 3 测试通过！")


if __name__ == "__main__":
    main()
