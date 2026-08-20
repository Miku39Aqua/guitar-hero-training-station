"""IR → alphaTex 转换器

将 ScoreIR 转换为 alphaTab 可渲染的 alphaTex 字符串。
alphaTex 语法要点：
- 音符：fret.string（如 3.3 表示 3 弦 3 品）
- 休止符：r
- 和弦：(note1 note2 note3)
- 时值：:duration 前缀改变后续所有 beat，或 .duration 后缀只改当前
- 小节分隔：|
- 元数据：\title "xxx" \tempo 120 等
"""

from __future__ import annotations

from .ir import ScoreIR, MeasureIR, BeatIR, NoteIR


def _note_to_alphatex(note: NoteIR) -> str:
    """单音转 alphaTex。技巧标记后续版本支持。"""
    s = f"{note.fret}.{note.string}"
    # 技巧标记（第一版只支持 mute，其他后续扩展）
    if note.technique == "mute":
        s += "{pm}"
    return s


def _beat_to_alphatex(beat: BeatIR) -> str:
    """单个 beat 转 alphaTex。"""
    if not beat.notes:
        return f"r.{beat.duration}"

    if len(beat.notes) == 1:
        note_str = _note_to_alphatex(beat.notes[0])
    else:
        # 和弦：括号包裹
        notes = " ".join(_note_to_alphatex(n) for n in beat.notes)
        note_str = f"({notes})"

    return f"{note_str}.{beat.duration}"


def _measure_to_alphatex(measure: MeasureIR) -> str:
    """单个小节转 alphaTex，以 | 结尾。"""
    beats = " ".join(_beat_to_alphatex(b) for b in measure.beats)
    return f"{beats} |"


def score_to_alphatex(ir: ScoreIR) -> str:
    """完整 ScoreIR → alphaTex 字符串。"""
    lines = []

    # 元数据
    lines.append(f'\\title "{ir.title}"')
    if ir.artist:
        lines.append(f'\\artist "{ir.artist}"')
    lines.append(f"\\tempo {ir.bpm}")
    lines.append(f"\\ts {ir.time_sig[0]} {ir.time_sig[1]}")

    # 调弦（非标准调弦时才输出）
    from .ir import STANDARD_TUNING
    if ir.tuning != STANDARD_TUNING:
        tuning_str = " ".join(str(t) for t in ir.tuning)
        lines.append(f"\\tuning {tuning_str}")

    # 谱面内容
    lines.append(".")  # 元数据与内容分隔点
    for measure in ir.measures:
        lines.append(_measure_to_alphatex(measure))

    return "\n".join(lines)


def score_to_alphatex_compact(ir: ScoreIR) -> str:
    """紧凑版：单行输出，适合 API 传输。"""
    lines = []

    # 元数据（每行一个，alphaTex 要求）
    lines.append(f'\\title "{ir.title}"')
    if ir.artist:
        lines.append(f'\\artist "{ir.artist}"')
    lines.append(f"\\tempo {ir.bpm}")
    lines.append(f"\\ts {ir.time_sig[0]} {ir.time_sig[1]}")

    # 内容
    lines.append(".")
    for measure in ir.measures:
        lines.append(_measure_to_alphatex(measure))

    return "\n".join(lines)
