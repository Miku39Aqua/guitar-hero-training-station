"""gp 谱面与 IR 的双向转换（PyGuitarPro 适配器）

- import_gp: .gp5/.gp4/.gp3 → IR（取第一条吉他轨、每个小节的第一声部）
- export_gp: IR → .gp5（兼容性最好，GTP6/7/8 与 TuxGuitar 均可打开）
"""

from __future__ import annotations

import guitarpro
from guitarpro.models import BeatStatus, NoteType

from .ir import ScoreIR, MeasureIR, BeatIR, NoteIR, STANDARD_TUNING


def import_gp(path: str) -> ScoreIR:
    """解析 gp 文件为 IR。默认取第一轨、每小节第一声部。"""
    song = guitarpro.parse(path)
    track = song.tracks[0]

    ir = ScoreIR(title=song.title or "Untitled",
                 artist=song.artist or "",
                 bpm=song.tempo or 120)
    if song.measureHeaders:
        ts = song.measureHeaders[0].timeSignature
        ir.time_sig = (ts.numerator, ts.denominator.value)
    if track.strings:
        ir.tuning = [s.value for s in track.strings]

    for m in track.measures:
        mir = MeasureIR()
        voices = [v for v in m.voices if v.beats]
        if not voices:
            continue
        for beat in voices[0].beats:
            bir = BeatIR(duration=beat.duration.value)
            if beat.status != BeatStatus.rest:
                for n in beat.notes:
                    if n.type == NoteType.normal:
                        bir.notes.append(NoteIR(string=n.string, fret=n.value))
            mir.beats.append(bir)
        ir.measures.append(mir)
    return ir


def export_gp(ir: ScoreIR, path: str) -> str:
    """把 IR 写出为 .gp5 文件，返回文件路径。

    注意 PyGuitarPro 的模型约定：
    1. Song() 默认自带 1 个空 header + 1 个空 track，且写出器按 tracks[0]
       的小节数写文件——必须用 Song(tracks=[], measureHeaders=[]) 清空默认
    2. Track 构造时会按 song.measureHeaders 自动生成 measures
    3. Beat.status 默认 empty 会被写出器跳过，Note.type 默认是 rest，
       都必须显式设置
    """
    from guitarpro.models import (Song, Track, MeasureHeader, Beat, Note,
                                  GuitarString, Duration, NoteType)

    song = Song(tracks=[], measureHeaders=[])
    song.title = ir.title
    song.artist = ir.artist
    song.tempo = ir.bpm

    # 1. 先建小节头（start 必须按拍点递增，否则写出器会合并小节）
    for i in range(len(ir.measures)):
        header = MeasureHeader()
        header.number = i + 1
        header.timeSignature.numerator = ir.time_sig[0]
        header.timeSignature.denominator.value = ir.time_sig[1]
        if i == 0:
            header.start = Duration.quarterTime
        else:
            prev = song.measureHeaders[-1]
            header.start = prev.start + prev.length
        song.measureHeaders.append(header)

    # 2. 建音轨（自动按 headers 生成 measures）
    track = Track(song, 1)
    track.strings = [GuitarString(i + 1, v)
                     for i, v in enumerate(ir.tuning or STANDARD_TUNING)]
    song.tracks.append(track)

    # 3. 往每个小节的第一声部填 beat
    for measure, mir in zip(track.measures, ir.measures):
        voice = measure.voices[0]
        for bir in mir.beats:
            beat = Beat(voice)
            beat.duration.value = bir.duration
            beat.status = BeatStatus.normal if bir.notes else BeatStatus.rest
            voice.beats.append(beat)
            for nir in bir.notes:
                note = Note(beat)
                note.type = NoteType.normal
                note.string = nir.string
                note.value = nir.fret
                beat.notes.append(note)

    guitarpro.write(song, path)
    return path
