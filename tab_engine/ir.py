"""谱面中间表示 (IR)

所有谱子来源（gp 文件解析 / 音频转谱）最终都汇入这个结构，
改编引擎、渲染器、导出器只跟 IR 打交道，彼此解耦。

时值约定：用分母表示，4=四分音符, 8=八分音符, 16=十六分音符。
弦编号约定：1~6，1 弦是高音 e（最细），6 弦是低音 E（最粗）。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
import json

# 标准调弦（从 1 弦到 6 弦的 MIDI 音高）
STANDARD_TUNING = [64, 59, 55, 50, 45, 40]  # e B G D A E


@dataclass
class NoteIR:
    string: int          # 1~6
    fret: int            # 0~24
    # 技巧标记（第一版只存旗标，导出 gp 时可逐步支持）
    technique: str | None = None  # "bend" | "slide" | "hammer" | "pull" | "mute"


@dataclass
class BeatIR:
    duration: int = 4               # 4=四分, 8=八分, 16=十六分
    notes: list[NoteIR] = field(default_factory=list)  # 空列表 = 休止符


@dataclass
class MeasureIR:
    beats: list[BeatIR] = field(default_factory=list)


@dataclass
class ScoreIR:
    title: str = "Untitled"
    artist: str = ""
    bpm: int = 120
    time_sig: tuple[int, int] = (4, 4)      # 拍号
    tuning: list[int] = field(default_factory=lambda: STANDARD_TUNING.copy())
    measures: list[MeasureIR] = field(default_factory=list)

    # ---- 序列化 ----
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, s: str) -> "ScoreIR":
        d = json.loads(s)
        score = cls(
            title=d["title"], artist=d.get("artist", ""), bpm=d["bpm"],
            time_sig=tuple(d["time_sig"]), tuning=d["tuning"],
        )
        for m in d["measures"]:
            measure = MeasureIR()
            for b in m["beats"]:
                beat = BeatIR(duration=b["duration"])
                beat.notes = [NoteIR(**n) for n in b["notes"]]
                measure.beats.append(beat)
            score.measures.append(measure)
        return score
