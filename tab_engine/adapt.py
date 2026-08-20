"""改编引擎：按用户画像约束降低谱面难度

这是"记忆影响结果"的核心证据模块（赛道 4）：
画像来自记忆系统（agent/memory.py 的画像层），改编规则是确定性代码，
每次改编产生 AdaptChange 记录，供 Agent 生成"根据你之前的反馈……"的解释。

画像字段（全部可选，缺省不启用对应规则）：
    no_barre: bool          横按规避：横按和弦简化为"根音+旋律音"双音
    max_fret: int           把位上限：超过的把位尝试同音换弦移回低把位
    max_note_duration: int  最快时值（如 8）：更快的音两两合并（弹一音休一音）
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from .ir import ScoreIR, MeasureIR, BeatIR, NoteIR


@dataclass
class AdaptChange:
    measure: int      # 第几小节（1 起）
    beat: int         # 第几拍（1 起）
    rule: str         # 触发的规则名
    before: str       # 改编前描述
    after: str        # 改编后描述


@dataclass
class AdaptReport:
    changes: list[AdaptChange] = field(default_factory=list)

    def summary_text(self) -> str:
        """给 Agent 引用的人类可读改编说明。"""
        if not self.changes:
            return "本次谱面无需改编，与你的能力画像完全匹配。"
        lines = ["根据你的能力画像，我做了以下改编："]
        for c in self.changes:
            lines.append(f"- 第{c.measure}小节第{c.beat}拍：{c.after}（{c.rule}）")
        return "\n".join(lines)


def _fmt_notes(notes: list[NoteIR]) -> str:
    if not notes:
        return "休止"
    return "+".join(f"{n.string}弦{n.fret}品" for n in notes)


def _is_barre(notes: list[NoteIR]) -> bool:
    """横按判定：同拍 >=3 个音，且最小非零品同时出现在 >=2 根弦上。"""
    if len(notes) < 3:
        return False
    frets = [n.fret for n in notes if n.fret > 0]
    if not frets:
        return False
    min_fret = min(frets)
    return sum(1 for f in frets if f == min_fret) >= 2


def _rule_no_barre(beat: BeatIR) -> bool:
    """横按和弦 → 只保留最低音弦（根音）和最高音弦（旋律音）。"""
    if not _is_barre(beat.notes):
        return False
    beat.notes.sort(key=lambda n: n.string, reverse=True)  # 弦号大=低音弦
    beat.notes[:] = [beat.notes[0], beat.notes[-1]]
    return True


def _rule_max_fret(beat: BeatIR, max_fret: int, tuning: list[int]) -> bool:
    """超把位的音 → 同音换到更低把位的弦上。"""
    changed = False
    for n in beat.notes:
        if n.fret <= max_fret:
            continue
        pitch = tuning[n.string - 1] + n.fret
        # 从高音弦(1)向低音弦(6)找：音高相同且品位不超上限的位置
        for s in range(1, 7):
            if s == n.string:
                continue
            new_fret = pitch - tuning[s - 1]
            if 0 <= new_fret <= max_fret:
                n.string, n.fret = s, new_fret
                changed = True
                break
    return changed


def _rule_simplify_fast(measure: MeasureIR, max_duration: int) -> list[int]:
    """比 max_duration 更快的音（如16分）两两合并：保留第一个音 + 补等长休止。

    返回被改写的 beat 序号（1 起）。总时值守恒。
    """
    changed_beats: list[int] = []
    new_beats: list[BeatIR] = []
    i = 0
    beats = measure.beats
    while i < len(beats):
        b = beats[i]
        if b.duration > max_duration and i + 1 < len(beats) \
                and beats[i + 1].duration > max_duration:
            merged = BeatIR(duration=max_duration, notes=b.notes)
            rest = BeatIR(duration=max_duration, notes=[])
            changed_beats.append(len(new_beats) + 1)
            new_beats.extend([merged, rest])
            i += 2
        elif b.duration > max_duration:
            # 落单的快音：直接放慢为 max_duration
            new_beats.append(BeatIR(duration=max_duration, notes=b.notes))
            changed_beats.append(len(new_beats))
            i += 1
        else:
            new_beats.append(b)
            i += 1
    measure.beats = new_beats
    return changed_beats


def adapt_difficulty(ir: ScoreIR, profile: dict) -> tuple[ScoreIR, AdaptReport]:
    """按画像约束改编谱面。返回 (改编后的新 IR, 改编报告)。不修改原 IR。"""
    out = copy.deepcopy(ir)
    report = AdaptReport()
    tuning = out.tuning

    for mi, measure in enumerate(out.measures, start=1):
        # 规则3：快速段落降级（整小节处理，会重建 beats，先行执行）
        max_dur = profile.get("max_note_duration")
        if max_dur:
            for bj in _rule_simplify_fast(measure, max_dur):
                report.changes.append(AdaptChange(
                    mi, bj, "快速段落降级",
                    f"快于1/{max_dur}的连续音符",
                    f"放慢为1/{max_dur}音符（弹一音休一音）"))

        # 规则1/2：逐 beat 处理
        for bj, beat in enumerate(measure.beats, start=1):
            if not beat.notes:
                continue
            before = _fmt_notes(beat.notes)
            if profile.get("no_barre") and _rule_no_barre(beat):
                report.changes.append(AdaptChange(
                    mi, bj, "横按规避", before,
                    f"横按和弦简化为双音 {_fmt_notes(beat.notes)}"))
                before = _fmt_notes(beat.notes)
            max_fret = profile.get("max_fret")
            if max_fret and _rule_max_fret(beat, max_fret, tuning):
                report.changes.append(AdaptChange(
                    mi, bj, "把位收敛", before,
                    f"移至低把位 {_fmt_notes(beat.notes)}"))

    return out, report
