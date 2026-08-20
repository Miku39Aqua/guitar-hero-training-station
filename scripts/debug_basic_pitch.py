"""调试 basic-pitch 返回结构（详细版）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import soundfile as sf

from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH

# 生成测试音频
sr = 44100
duration = 2.0
freqs = [261.63, 392.00, 440.00, 392.00]
note_dur = duration / len(freqs)
t = np.linspace(0, note_dur, int(sr * note_dur), False)
audio = np.concatenate([0.3 * np.sin(2 * np.pi * f * t) for f in freqs])
sf.write("output/test_basic_pitch.wav", audio, sr)

print("=== 调用 basic-pitch ===")
model_output = predict("output/test_basic_pitch.wav", model_or_model_path=ICASSP_2022_MODEL_PATH)

print(f"返回类型: {type(model_output)}")
print(f"返回长度: {len(model_output)}")
for i, item in enumerate(model_output):
    print(f"\n--- item[{i}] ---")
    print(f"  类型: {type(item)}")
    if isinstance(item, dict):
        print(f"  键: {list(item.keys())}")
        for k, v in item.items():
            if isinstance(v, list):
                print(f"    {k}: list[{len(v)}]")
                if len(v) > 0:
                    print(f"      第一个: {v[0]}")
            else:
                print(f"    {k}: {v}")
    elif hasattr(item, 'shape'):
        print(f"  形状: {item.shape}")
        print(f"  dtype: {item.dtype}")
    elif isinstance(item, (list, tuple)) and len(item) > 0:
        print(f"  长度: {len(item)}")
        print(f"  第一个元素类型: {type(item[0])}")
        if isinstance(item[0], (list, tuple)):
            print(f"  第一个元素值: {item[0][:5]}")
        else:
            print(f"  第一个元素值: {item[0]}")
    else:
        print(f"  值: {item}")
