"""Stage 3: 指法引擎（动态规划，最小可运行版）"""
from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR, STANDARD_TUNING


# 标准调弦 MIDI 音高（空弦）
OPEN_STRING_MIDI = [64, 59, 55, 50, 45, 40]  # e2=40, B1=45, G1=50, D2=55, A2=59, E3=64

# alphaTex 支持的时值分母（2 的幂次）
VALID_DURATIONS = [1, 2, 4, 8, 16, 32, 64, 128, 256]


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


def quantize_duration(duration_beats: float) -> int:
    """把以拍为单位的时值量化成 alphaTex 支持的分母。"""
    if duration_beats <= 0:
        duration_beats = 0.25
    # duration_beats = 4 / denominator
    raw_denom = 4.0 / duration_beats
    closest = min(VALID_DURATIONS, key=lambda d: abs(d - raw_denom))
    return closest


def midi_notes_to_ir(midi_notes: list[dict], bpm: int = 120, title: str = "Transcribed") -> ScoreIR:
    """将 basic-pitch 输出的 MIDI 音符列表转换为 ScoreIR。

    节奏处理策略：
    - 把所有音符按开始时间排序
    - 按时间顺序生成 beat，每个 beat 的时值根据音符实际长度量化
    - 同一时刻开始、长度相近的音符合并为和弦
    - 不同时间点的音符放到不同 beat
    """
    if not midi_notes:
        return ScoreIR(title=f"{title} (no notes)", artist="", bpm=bpm)

    ir = ScoreIR(title=title, artist="", bpm=int(round(bpm)))

    # 按开始时间排序
    notes = sorted(midi_notes, key=lambda n: (n["start"], n["pitch"]))

    beat_duration = 60.0 / bpm
    measures: list[MeasureIR] = []

    # 按开始时间分组，同一时刻（容差 50ms）开始的音符合并成和弦
    tolerance = 0.05  # 50ms
    note_groups = []
    current_group = [notes[0]]
    for note in notes[1:]:
        if abs(note["start"] - current_group[0]["start"]) <= tolerance:
            current_group.append(note)
        else:
            note_groups.append(current_group)
            current_group = [note]
    note_groups.append(current_group)

    # 当前小节和拍累计
    current_beat_time = 0.0  # 当前 beat 在歌曲中的开始时间（秒）
    current_measure = MeasureIR()
    current_measure_beats = 0.0  # 当前小节已占用的拍数
    measure_capacity = 4.0  # 4/4 拍

    for group in note_groups:
        start_time = group[0]["start"]
        # 该和弦的时长取组内最短音符
        min_duration = min(n["duration"] for n in group)
        duration_beats = min_duration / beat_duration
        duration = quantize_duration(duration_beats)

        # 计算这个 beat 应该放在哪个小节
        # 如果 start_time 超出了当前小节容量，先补休止符并推进到正确小节
        start_beat_global = start_time / beat_duration

        # 找到应该插入的小节位置
        target_measure_idx = int(start_beat_global // 4)
        target_beat_in_measure = start_beat_global % 4

        # 确保小节存在
        while len(measures) <= target_measure_idx:
            # 先把当前小节补满休止符
            if current_measure_beats < measure_capacity:
                remaining = measure_capacity - current_measure_beats
                # 用一个休止符填满
                current_measure.beats.append(BeatIR(duration=quantize_duration(remaining), notes=[]))
            measures.append(current_measure)
            current_measure = MeasureIR()
            current_measure_beats = 0.0

        # 如果当前小节已经有内容但不是目标小节，说明前面有空白，已经补过了
        # 现在在目标小节里插入 beat
        # 如果需要，在小节开头补休止符
        if target_beat_in_measure > current_measure_beats + 0.01:
            gap = target_beat_in_measure - current_measure_beats
            current_measure.beats.append(BeatIR(duration=quantize_duration(gap), notes=[]))
            current_measure_beats = target_beat_in_measure

        # 构建和弦
        beat = BeatIR(duration=duration)
        for note in group:
            sf = midi_to_string_fret(note["pitch"])
            if sf is None:
                continue
            string, fret = sf
            # 避免同一弦重复音符
            if not any(n.string == string for n in beat.notes):
                beat.notes.append(NoteIR(string=string, fret=fret))

        if beat.notes:
            current_measure.beats.append(beat)
            current_measure_beats += 4.0 / duration

            # 如果小节满了，推到 measures
            if current_measure_beats >= measure_capacity - 0.01:
                measures.append(current_measure)
                current_measure = MeasureIR()
                current_measure_beats = 0.0

    # 处理最后一个小节
    if current_measure.beats or current_measure not in measures:
        if current_measure_beats < measure_capacity:
            remaining = measure_capacity - current_measure_beats
            current_measure.beats.append(BeatIR(duration=quantize_duration(remaining), notes=[]))
        measures.append(current_measure)

    ir.measures = measures
    return ir
