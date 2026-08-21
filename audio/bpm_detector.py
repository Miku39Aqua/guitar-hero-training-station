"""基于离散小波变换的 BPM 检测（兼容 MP3/FLAC/WAV）。

算法来自: https://github.com/scaperot/the-BPM-detector-python
论文: G. Tzanetakis, G. Essl and P. Cook, "Audio Analysis using the Discrete Wavelet Transform"
"""
import math

import librosa
import numpy as np
import pywt
from scipy import signal


def _peak_detect(data: np.ndarray):
    max_val = np.amax(abs(data))
    peak_ndx = np.where(data == max_val)
    if len(peak_ndx[0]) == 0:
        peak_ndx = np.where(data == -max_val)
    return peak_ndx


def _bpm_from_window(data: np.ndarray, fs: int):
    levels = 4
    max_decimation = 2 ** (levels - 1)
    min_ndx = math.floor(60.0 / 220 * (fs / max_decimation))
    max_ndx = math.floor(60.0 / 40 * (fs / max_decimation))

    cD_sum = None
    cA = data

    for loop in range(levels):
        cA, cD = pywt.dwt(cA, "db4")

        if loop == 0:
            cD_minlen = len(cD) / max_decimation + 1
            cD_sum = np.zeros(math.floor(cD_minlen))

        cD = signal.lfilter([0.01], [1 - 0.99], cD)
        cD = abs(cD[:: (2 ** (levels - loop - 1))])
        cD = cD - np.mean(cD)
        cD_sum = cD[0 : math.floor(cD_minlen)] + cD_sum

    if all(b == 0.0 for b in cA):
        return None

    cA = signal.lfilter([0.01], [1 - 0.99], cA)
    cA = abs(cA)
    cA = cA - np.mean(cA)
    cD_sum = cA[0 : math.floor(cD_minlen)] + cD_sum

    correl = np.correlate(cD_sum, cD_sum, "full")
    midpoint = math.floor(len(correl) / 2)
    correl_midpoint_tmp = correl[midpoint:]
    peak_ndx = _peak_detect(correl_midpoint_tmp[min_ndx:max_ndx])
    if len(peak_ndx) > 1:
        return None

    peak_ndx_adjusted = peak_ndx[0] + min_ndx
    bpm = 60.0 / peak_ndx_adjusted * (fs / max_decimation)
    return float(bpm)


def estimate_bpm(audio_path: str, window_seconds: float = 3.0) -> float:
    """估计音频文件的 BPM。

    Args:
        audio_path: 音频文件路径（支持 mp3/flac/wav 等 librosa 支持的格式）
        window_seconds: 每个分析窗口的时长（秒），默认 3 秒

    Returns:
        BPM 估计值，失败时返回 120.0
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        if len(y) == 0:
            return 120.0

        nsamps = len(y)
        window_samps = int(window_seconds * sr)
        if window_samps > nsamps:
            window_samps = nsamps

        max_window_ndx = math.floor(nsamps / window_samps)
        if max_window_ndx == 0:
            max_window_ndx = 1

        bpms = []
        for window_ndx in range(max_window_ndx):
            start = window_ndx * window_samps
            end = start + window_samps
            data = y[start:end]
            bpm = _bpm_from_window(data, sr)
            if bpm is not None and 40 <= bpm <= 220:
                bpms.append(bpm)

        if not bpms:
            return 120.0

        return float(np.median(bpms))
    except Exception as e:
        print(f"[BPM Detector] 失败: {e}")
        return 120.0
