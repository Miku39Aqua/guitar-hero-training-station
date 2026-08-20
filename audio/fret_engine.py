"""Stage 3: 指法引擎（动态规划，最小可运行版）"""
from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR, STANDARD_TUNING


# 标准调弦 MIDI 音高（空弦）
OPEN_STRING_MIDI = [64, 59, 55, 50, 45, 40]  # e2=40, B1=45, G1=50, D2=55, A2=59, E3=64


def midi_to_string_fret(midi_pitch: int) -> tuple[int, int] | None:
    """将 MIDI 音高转换为 (弦, 品)。优先低把位，同一音高优先粗弦。"""
    best = None
    best_cost = 9999

    for string, open_midi in enumerate(OPEN_STRING_MIDI, start=1):
        fret = midi_pitch - open_midi
        if 0 <= fret <= 24:
            # 成本：品位数 + 弦惩罚（细弦更难按）
            string_penalty = (7 - string) * 0.5
            cost = fret + string_penalty
            if cost < best_cost:
                best_cost = cost
                best = (string, fret)

    return best


def midi_notes_to_ir(midi_notes: list[dict], bpm: int = 120) -> ScoreIR:
    """将 basic-pitch 输出的 MIDI 音符列表转换为 ScoreIR。"""
    if not midi_notes:
        return ScoreIR(title="Transcribed (no notes)", artist="", bpm=bpm)

    ir = ScoreIR(title="Transcribed", artist="", bpm=bpm)

    notes = sorted(midi_notes, key=lambda n: n["start"])

    beat_duration = 60.0 / bpm
    measures = []
    current_measure = None

    for note in notes:
        start_beat = note["start"] / beat_duration
        duration_beats = note["duration"] / beat_duration

        # 量化到 1/4 beat
        duration_beats = max(1, round(duration_beats * 4) / 4)

        sf = midi_to_string_fret(note["pitch"])
        if sf is None:
            continue

        string, fret = sf

        # 计算小节/beat（简化：4/4 拍，每小节 4 拍）
        measure_idx = int(start_beat) // 4
        beat_idx = int(start_beat) % 4

        # 确保小节存在
        while len(measures) <= measure_idx:
            measures.append(MeasureIR(beats=[BeatIR(duration=4, notes=[]) for _ in range(4)]))

        beat = measures[measure_idx].beats[beat_idx]
        # 如果 beat 已有音符，合并（双音/和弦）
        beat.notes.append(NoteIR(string=string, fret=fret))
        # 取最大 duration
        if duration_beats > beat.duration / 4:
            beat.duration = int(duration_beats * 4)

    ir.measures = measures
    return ir
