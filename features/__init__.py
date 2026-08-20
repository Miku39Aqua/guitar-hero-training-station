"""曲子特征库

每个曲子是一个 JSON 文件，包含：
- style_vector: 风格向量（ACG/摇滚/流行/爵士 等维度 0~1）
- era: 年代（2010s / 2020s）
- techniques: 技巧标签列表（横按/扫弦/分解和弦/点弦）
- bpm: 曲速
- key: 调性（C major / A minor 等）
- difficulty: 难度 1~5
"""
import json
from pathlib import Path

FEATURES_DIR = Path(__file__).parent.parent / "features"
FEATURES_DIR.mkdir(exist_ok=True)


def get_all_features() -> list[dict]:
    """读取所有曲子特征。"""
    results = []
    for f in FEATURES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.stem
            results.append(data)
        except Exception:
            pass
    return results


def get_feature(title: str) -> dict | None:
    """按标题查找特征。"""
    path = FEATURES_DIR / f"{title}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def add_or_update_feature(title: str, **kwargs) -> dict:
    """新增或更新曲子特征。"""
    path = FEATURES_DIR / f"{title}.json"
    existing = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing.update(kwargs)
    existing.setdefault("title", title)
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    return existing
