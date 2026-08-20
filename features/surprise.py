"""意外选曲引擎

算法：
1. 计算用户历史偏好向量（基于画像 + 已弹曲子风格加权）
2. 计算每首候选曲子的意外度 = 风格距离 × 技术匹配度
3. 过滤掉已经弹过的曲子（如果有记录）
4. 排序选 top1 + 生成可解释理由
"""
import os
import json
import math
from pathlib import Path
from typing import Optional

from features import get_all_features, get_feature
import agent.memory as memory


# ========== 向量工具 ==========

def _cosine(a: dict, b: dict) -> float:
    """两个 style_vector 的余弦相似度"""
    if not a or not b:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    keys = set(a.keys()) | set(b.keys())
    for k in keys:
        x = float(a.get(k, 0.0))
        y = float(b.get(k, 0.0))
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _build_user_style_vector() -> dict:
    """从记忆系统构建用户当前风格偏好向量"""
    profile = memory._load_profile()
    # 画像里可能直接有 style_vector
    user_vec = {}
    if "style_vector" in profile and isinstance(profile["style_vector"], dict):
        user_vec.update(profile["style_vector"])

    # 从 episodes 推断：把历史 input 当曲子名，读取其特征向量加权
    try:
        conn = memory._get_conn()
        cursor = conn.execute("SELECT input, feedback FROM episodes")
        rows = cursor.fetchall()
        conn.close()
    except Exception:
        rows = []

    for row in rows:
        input_text = row[0]
        feedback = row[1] or ""
        # 尝试把 input 当文件名查特征库
        feat = get_feature(input_text)
        if not feat:
            # 尝试直接当标题查（去掉扩展名等情况）
            for f in Path(__file__).parent.parent.glob("features/*.json"):
                stem = f.stem
                if stem.lower() in input_text.lower() or input_text.lower() in stem.lower():
                    try:
                        feat = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                    if feat:
                        break
        if feat and "style_vector" in feat:
            sv = feat["style_vector"]
            # feedback 里带"喜欢"则加倍权
            weight = 1.0
            if any(k in feedback for k in ["喜欢", "不错", "好听", "棒", "赞", "good"]):
                weight = 1.5
            elif any(k in feedback for k in ["讨厌", "难", "不行", "不喜欢"]):
                weight = 0.3
            for k, v in sv.items():
                user_vec[k] = user_vec.get(k, 0.0) + float(v) * weight

    # 归一化
    norm = math.sqrt(sum(v * v for v in user_vec.values()))
    if norm > 0:
        user_vec = {k: v / norm for k, v in user_vec.items()}
    return user_vec


def _build_played_titles() -> set:
    """从 episodes 中提取已经弹过的曲目标题集合"""
    played = set()
    try:
        conn = memory._get_conn()
        cursor = conn.execute("SELECT input FROM episodes")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            if row[0]:
                played.add(row[0].strip().lower())
    except Exception:
        pass
    return played


def _tech_match_score(features: dict, user_profile: dict) -> float:
    """技术匹配度：基于难度、技巧、BPM 与用户画像的匹配"""
    score = 1.0

    # 难度：用户画像里 difficulty_max 限制
    diff = features.get("difficulty", 3)
    max_diff = user_profile.get("difficulty_max", 5)
    if isinstance(max_diff, str):
        try:
            max_diff = int(max_diff)
        except Exception:
            max_diff = 5
    if diff > max_diff:
        score *= 0.5

    # 技巧：用户不能做的技巧降权
    avoid_tech = set()
    rules = memory._load_rules()
    for rule in rules:
        text = rule.get("text", "")
        if "横按" in text or "大横按" in text:
            avoid_tech.add("横按")
        if "扫弦" in text or "十六分" in text:
            avoid_tech.add("扫弦")
        if "点弦" in text:
            avoid_tech.add("点弦")
        if "推弦" in text:
            avoid_tech.add("推弦")

    techniques = features.get("techniques", [])
    if techniques and avoid_tech:
        overlap = len(set(techniques) & avoid_tech)
        if overlap > 0:
            score *= max(0.3, 1.0 - overlap * 0.3)

    return min(score, 1.0)


def _explain_surprise(user_vec: dict, feat: dict, score: float) -> str:
    """生成推荐理由"""
    reasons = []
    sv = feat.get("style_vector", {})

    # 风格差异亮点
    for style, val in sv.items():
        user_val = user_vec.get(style, 0.0)
        if val > 0.6 and user_val < 0.3:
            reasons.append(f"含有较多「{style}」元素")
            break

    # 难度/技巧亮点
    diff = feat.get("difficulty")
    if diff is not None:
        if diff <= 2:
            reasons.append("难度较低，适合练习")
        elif diff >= 4:
            reasons.append("有一定挑战性")

    # 年代/新鲜度
    era = feat.get("era")
    if era:
        reasons.append(f"来自{era}")

    # 默认理由
    if not reasons:
        reasons.append("风格与你的常用曲风差异较大")

    # 意外度分档
    if score > 0.8:
        prefix = "完全超出你的舒适区："
    elif score > 0.6:
        prefix = "有点意外，但值得一试："
    elif score > 0.4:
        prefix = "风格略有不同："
    else:
        prefix = "虽然差异不算太大，但："
    return prefix + "；".join(reasons)


# ========== 公开接口 ==========

def surprise_me(top_k: int = 5) -> Optional[dict]:
    """
    核心推荐算法。
    返回：
    {
        "title": "推荐曲名",
        "artist": "艺术家",
        "surprise_score": 0.82,
        "reason": "推荐理由",
        "features": {...}
    }
    如果没有候选，返回 None。
    """
    import random
    random.seed()

    all_songs = get_all_features()
    if not all_songs:
        return None

    user_vec = _build_user_style_vector()
    played = _build_played_titles()
    user_profile = memory._load_profile()

    # 统计曲库中各风格的稀有度（风格值>0.6 的曲子数，越少越稀有）
    style_counts = {}
    for feat in all_songs:
        for style, val in feat.get("style_vector", {}).items():
            if val > 0.6:
                style_counts[style] = style_counts.get(style, 0) + 1
    total_songs = len(all_songs)
    style_rarity = {}
    for style, count in style_counts.items():
        style_rarity[style] = 1.0 - (count / max(total_songs, 1))

    candidates = []
    for feat in all_songs:
        title = feat.get("title", feat.get("_filename", ""))
        if title.lower() in played:
            continue

        sv = feat.get("style_vector", {})
        # 风格距离 = 1 - 余弦相似度
        if user_vec:
            sim = _cosine(user_vec, sv)
            style_distance = max(0.0, 1.0 - sim)
        else:
            # 冷启动：用户无历史，用风格稀有度 + 随机扰动代替
            rarity_bonus = sum(style_rarity.get(s, 0.0) * v for s, v in sv.items())
            style_distance = 0.5 + rarity_bonus * 0.5 + random.uniform(0.0, 0.3)
            style_distance = min(style_distance, 1.0)

        tech_match = _tech_match_score(feat, user_profile)
        # 基础分
        base = style_distance * (1.05 - tech_match)
        # 随机扰动（±0.1）
        noise = random.uniform(-0.1, 0.1)
        surprise_score = max(0.0, min(1.0, base + noise))

        candidates.append({
            "title": title,
            "artist": feat.get("artist", ""),
            "surprise_score": round(surprise_score, 3),
            "features": feat,
        })

    if not candidates:
        return None

    candidates.sort(key=lambda x: x["surprise_score"], reverse=True)
    top = candidates[0]

    return {
        "title": top["title"],
        "artist": top["artist"],
        "surprise_score": top["surprise_score"],
        "reason": _explain_surprise(user_vec, top["features"], top["surprise_score"]),
        "features": top["features"],
    }
