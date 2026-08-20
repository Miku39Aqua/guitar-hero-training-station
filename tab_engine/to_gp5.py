"""ScoreIR → gp5 导出器

将谱面中间表示 (ScoreIR) 写出为 Guitar Pro 5 格式文件。
复用 tab_engine.gp_io 里的 PyGuitarPro 写文件逻辑，并显式指定 utf-8 编码以支持中文标题。
"""

from .ir import ScoreIR, MeasureIR, BeatIR, NoteIR, STANDARD_TUNING


def ir_to_gp5(ir: ScoreIR, output_path: str) -> str:
    """将 ScoreIR 对象写出为 .gp5 文件，返回生成的文件路径。

    注意：PyGuitarPro 的 guitarpro.write 默认使用 cp1252 编码，
    中文标题会报 UnicodeEncodeError，因此此处显式传入 encoding='utf-8'。
    """
    import guitarpro
    from guitarpro.models import (Song, Track, MeasureHeader, Beat, Note,
                                  GuitarString, Duration, NoteType)
    from guitarpro.models import BeatStatus

    song = Song(tracks=[], measureHeaders=[])
    song.title = ir.title
    song.artist = ir.artist
    song.tempo = ir.bpm

    # 1. 先建小节头
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

    # 2. 建音轨
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

    guitarpro.write(song, output_path, encoding='utf-8')
    return output_path
