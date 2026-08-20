"""验证 gp5 导出器"""
import sys
sys.path.insert(0, r"c:\Users\Miku39sjc\Desktop\hackson")

from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR
from tab_engine.to_gp5 import ir_to_gp5
import os

ir = ScoreIR(title="God Knows", artist="凉宫春日", bpm=172)
for i in range(4):
    m = MeasureIR(beats=[
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=0)]),
        BeatIR(duration=4, notes=[NoteIR(string=3, fret=2)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=0)]),
        BeatIR(duration=4, notes=[NoteIR(string=2, fret=1)]),
    ])
    ir.measures.append(m)

out = r"c:\Users\Miku39sjc\Desktop\hackson\output\test_export.gp5"
ir_to_gp5(ir, out)
size = os.path.getsize(out)
print(f"导出成功: {out}")
print(f"文件大小: {size} bytes")
