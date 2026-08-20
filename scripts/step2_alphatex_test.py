"""IR → alphaTex 转换器测试

构造测试 IR → 转 alphaTex → 输出到文件供浏览器验证
运行: python scripts/step2_alphatex_test.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR
from tab_engine.to_alphatex import score_to_alphatex, score_to_alphatex_compact


def build_test_score() -> ScoreIR:
    """构造一个包含多种场景的测试谱"""
    ir = ScoreIR(title="alphaTex 测试曲", artist="测试", bpm=120)

    # 小节1: 单音旋律
    m1 = MeasureIR(beats=[
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=0)]),
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=2)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=0)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=1)]),
    ])
    ir.measures.append(m1)

    # 小节2: 和弦
    m2 = MeasureIR(beats=[
        BeatIR(duration=4, notes=[
            NoteIR(string=6, fret=0),
            NoteIR(string=5, fret=2),
            NoteIR(string=4, fret=2),
            NoteIR(string=3, fret=0),
        ]),
        BeatIR(duration=4, notes=[
            NoteIR(string=5, fret=0),
            NoteIR(string=4, fret=2),
            NoteIR(string=3, fret=2),
            NoteIR(string=2, fret=0),
        ]),
        BeatIR(duration=2, notes=[NoteIR(string=1, fret=0)]),
    ])
    ir.measures.append(m2)

    # 小节3: 混合时值 + 休止
    m3 = MeasureIR(beats=[
        BeatIR(duration=8, notes=[NoteIR(string=3, fret=2)]),
        BeatIR(duration=8, notes=[NoteIR(string=3, fret=4)]),
        BeatIR(duration=4),
        BeatIR(duration=2, notes=[NoteIR(string=4, fret=0)]),
    ])
    ir.measures.append(m3)

    return ir


def main():
    ir = build_test_score()

    print("=== 测试 IR 结构 ===")
    for i, m in enumerate(ir.measures, 1):
        parts = []
        for b in m.beats:
            notes = "+".join(f"{n.string}s{n.fret}f" for n in b.notes) or "rest"
            parts.append(f"[1/{b.duration} {notes}]")
        print(f"  小节{i}: " + " ".join(parts))

    print("\n=== alphaTex（标准版）===")
    alphatex = score_to_alphatex(ir)
    print(alphatex)

    print("\n=== alphaTex（紧凑版）===")
    compact = score_to_alphatex_compact(ir)
    print(compact)

    # 写入文件供浏览器测试
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, "test.alphatex"), "w", encoding="utf-8") as f:
        f.write(alphatex)
    print(f"\n已写入 output/test.alphatex")

    # 生成一个带 alphaTab 的测试 HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>alphaTex 测试</title>
    <script src="https://cdn.jsdelivr.net/npm/@coderline/alphatab@latest/dist/alphaTab.js"></script>
    <style>
        body {{ font-family: sans-serif; padding: 20px; }}
        #score {{ width: 100%; }}
        textarea {{ width: 100%; height: 150px; margin-top: 20px; font-family: monospace; }}
    </style>
</head>
<body>
    <h1>alphaTex 渲染测试</h1>
    <div id="score"></div>
    <h3>alphaTex 源码：</h3>
    <textarea readonly>{alphatex}</textarea>
    <script>
        const alphatex = document.querySelector('textarea').value;
        const el = document.getElementById('score');
        const api = new alphaTab.AlphaTabApi(el, {{
            core: {{ tex: true }},
            display: {{
                layoutMode: alphaTab.LayoutMode.Page,
                staveProfile: alphaTab.StaveProfile.ScoreTab,
            }},
        }});
        api.tex(alphatex);
    </script>
</body>
</html>"""
    with open(os.path.join(output_dir, "test_alphatex.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已写入 output/test_alphatex.html（用浏览器打开验证渲染）")

    # 断言
    assert "\\title" in alphatex
    assert "\\tempo 120" in alphatex
    assert "|" in alphatex
    assert "0.3.4" in alphatex or "0.3" in alphatex  # 3弦0品
    print("\nOK: 转换器基础断言通过")


if __name__ == "__main__":
    main()
