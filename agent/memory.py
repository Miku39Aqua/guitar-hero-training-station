"""记忆系统接口实现

三层记忆：
- 画像层 data/profile.json   扁平 JSON
- 规则层 data/rules.json     规则列表，写入前做向量相似度去重
- 情景层 data/episodes.db    sqlite3 向量库（自实现向量检索）

成本埋点：所有 LLM 调用与记忆读写追加到 data/memory_log.jsonl
"""

import os
import json
import time
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

# ========== 路径与可配置参数 ==========
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROFILE_PATH = DATA_DIR / "profile.json"
RULES_PATH = DATA_DIR / "rules.json"
EPISODES_DB_PATH = DATA_DIR / "episodes.db"
LOG_PATH = DATA_DIR / "memory_log.jsonl"

# 每层注入条数可通过环境变量配置（控制 token 成本）
MAX_RULES = int(os.getenv("MEMORY_MAX_RULES", "3"))
MAX_EPISODES = int(os.getenv("MEMORY_MAX_EPISODES", "2"))

_log_lock = threading.Lock()
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ========== 成本埋点 ==========
def _log_cost(op: str, tokens_in: int = 0, tokens_out: int = 0,
              latency_ms: float = 0, detail: str = "") -> None:
    """追加一行成本日志到 data/memory_log.jsonl"""
    entry = {
        "ts": datetime.now().isoformat(),
        "op": op,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": round(latency_ms, 2),
        "detail": detail
    }
    try:
        with _log_lock:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ========== 画像层 I/O ==========
def _load_profile() -> dict:
    """读取画像层，文件不存在或异常时返回空字典"""
    if not PROFILE_PATH.exists():
        return {}
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_profile(profile: dict) -> None:
    """写入画像层"""
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


# ========== 规则层 I/O ==========
def _load_rules() -> list:
    """读取规则层"""
    if not RULES_PATH.exists():
        return []
    try:
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_rules(rules: list) -> None:
    """写入规则层"""
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


# ========== 情景层 I/O（标准 sqlite3 + 自实现向量） ==========
def _get_conn() -> sqlite3.Connection:
    """获取数据库连接，自动建表"""
    conn = sqlite3.connect(str(EPISODES_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            input TEXT,
            feedback TEXT,
            embedding BLOB,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


def _vector_to_blob(vec: list) -> bytes:
    """向量转 BLOB"""
    return bytes(vec)


def _blob_to_vector(blob: bytes) -> list:
    """BLOB 转向量"""
    return list(blob)


# ========== Embedding（优先 LLM，降级 n-gram 哈希） ==========
_llm_available = True  # 全局标记，避免失败后反复尝试


def _get_embedding(text: str) -> list:
    """
    获取文本 embedding，优先调用 LLM embedding 接口；
    若不可用，降级为字符级 n-gram 哈希向量（512 维）。
    """
    global _llm_available
    if not _llm_available:
        return _ngram_hash_vector(text, dim=512)

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            timeout=10,
        )
        model = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-3-small")
        start = time.time()
        resp = client.embeddings.create(input=text, model=model, timeout=10)
        latency = (time.time() - start) * 1000

        vec = list(resp.data[0].embedding)
        if len(vec) > 512:
            vec = vec[:512]
        while len(vec) < 512:
            vec.append(0.0)
        vec = [float(v) for v in vec]

        _log_cost(
            op="embedding",
            tokens_in=getattr(getattr(resp, "usage", None), "prompt_tokens", 0),
            tokens_out=0,
            latency_ms=latency,
            detail="llm_embedding"
        )
        return vec
    except Exception:
        _llm_available = False
        return _ngram_hash_vector(text, dim=512)


def _ngram_hash_vector(text: str, dim: int = 512) -> list:
    """字符级 n-gram 哈希向量（离线降级方案）"""
    vec = [0.0] * dim
    text = text.lower().strip()
    # 2-gram
    for i in range(max(0, len(text) - 1)):
        gram = text[i:i + 2]
        idx = hash(gram) % dim
        vec[idx] += 1.0
    # 单字加权
    for ch in text:
        idx = hash(ch) % dim
        vec[idx] += 0.5
    # 归一化
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def _cosine_similarity(a: list, b: list) -> float:
    """余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ========== LLM 提炼 ==========
def _call_llm_for_distill(user_input: str, agent_output: str,
                          user_feedback: str) -> Optional[dict]:
    """
    调用 LLM 从用户反馈中提炼记忆。
    返回 {"type": "profile"|"rule"|"episode"|"none", "content": "..."}。
    LLM 不可用时降级到本地规则匹配。
    """
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", ""),
            api_key=os.getenv("LLM_API_KEY", ""),
            timeout=10,
        )
        model = os.getenv("LLM_MODEL", "deepseek-chat")

        prompt = (
            "你是一个吉他练习记忆提炼助手。请从用户的反馈中提炼结构化记忆。\n\n"
            f"用户输入：{user_input}\n"
            f"Agent 输出：{agent_output}\n"
            f"用户反馈：{user_feedback}\n\n"
            "请判断反馈中是否包含值得长期记忆的信息，输出 JSON：\n"
            '{"type": "profile"|"rule"|"episode"|"none", "content": "提炼后的记忆内容"}\n\n'
            "type 说明：\n"
            "- profile: 用户偏好/限制（如'我按不了大横按'、'我不喜欢高增益音色'）\n"
            "- rule: 可复用的演奏规则（如'十六分扫弦降级为八分'）\n"
            "- episode: 具体练习事件（如'上次弹《蓝色星球》第12小节跨把位失败，已改为滑弦'）\n"
            "- none: 无提炼价值\n\n"
            "只输出 JSON，不要其他内容。"
        )

        start = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=10,
        )
        latency = (time.time() - start) * 1000

        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        result = json.loads(content)

        _log_cost(
            op="distill",
            tokens_in=getattr(getattr(resp, "usage", None), "prompt_tokens", 0),
            tokens_out=getattr(getattr(resp, "usage", None), "completion_tokens", 0),
            latency_ms=latency,
            detail=f"llm_distill_type={result.get('type', 'unknown')}"
        )
        return result
    except Exception as e:
        _log_cost(
            op="distill",
            tokens_in=0,
            tokens_out=0,
            latency_ms=0,
            detail=f"llm_fallback_local:{str(e)}"
        )
        return _local_distill_fallback(user_input, agent_output, user_feedback)


def _local_distill_fallback(user_input: str, agent_output: str,
                            user_feedback: str) -> Optional[dict]:
    """本地降级提炼（无 LLM 时的 fallback）"""
    fb = user_feedback.strip()
    if not fb:
        return {"type": "none", "content": ""}

    # 偏好/限制类
    if any(k in fb for k in ["不喜欢", "讨厌", "不了", "不能", "没法学", "太", "难"]):
        if "音色" in fb or "增益" in fb or "失真" in fb:
            return {"type": "profile", "content": f"音色偏好:{fb}"}
        if "横按" in fb or "大横按" in fb:
            return {"type": "profile", "content": f"手型限制:{fb}"}
        if "十六分" in fb or "扫弦" in fb or "速度" in fb or "太快" in fb:
            rule_text = fb.replace("我弹不了", "").replace("这段", "").strip()
            if not rule_text:
                rule_text = "十六分音符降级为八分"
            return {"type": "rule", "content": rule_text}

    # 具体事件类
    if any(k in fb for k in ["失败", "改成", "改为", "改用", "不行"]):
        return {"type": "episode", "content": f"上次练习反馈:{fb}"}

    return {"type": "none", "content": ""}


# ========== 公开 API ==========

def retrieve(query: str) -> str:
    """
    检索与当前任务相关的记忆，拼装为注入 system prompt 的上下文字符串。
    画像层全量注入；规则层按 query 向量相似度取 top-3；情景层取 top-2。
    每层注入条数可通过环境变量 MEMORY_MAX_RULES / MEMORY_MAX_EPISODES 配置。
    """
    parts = []

    # 1. 画像层（全量注入）
    try:
        profile = _load_profile()
        if profile:
            profile_parts = [f"{k}:{v}" for k, v in profile.items()]
            parts.append("【用户画像】" + " | ".join(profile_parts))
    except Exception as e:
        _log_cost(op="retrieve", detail=f"profile_load_error:{str(e)}")

    # 2. 规则层（向量相似度 top-N）
    try:
        rules = _load_rules()
        if rules and query:
            query_vec = _get_embedding(query)
            scored = []
            for rule in rules:
                rule_text = rule.get("text", "")
                rule_vec = _get_embedding(rule_text)
                sim = _cosine_similarity(query_vec, rule_vec)
                scored.append((sim, rule))
            scored.sort(key=lambda x: x[0], reverse=True)
            top_rules = scored[:MAX_RULES]
            if top_rules:
                rule_strs = [
                    f"{i+1}. {r[1].get('text', '')}"
                    for i, r in enumerate(top_rules)
                ]
                parts.append("【相关规则】" + "\n".join(rule_strs))
    except Exception as e:
        _log_cost(op="retrieve", detail=f"rules_retrieve_error:{str(e)}")

    # 3. 情景层（向量相似度 top-N）
    try:
        conn = _get_conn()
        cursor = conn.execute("SELECT input, feedback, embedding FROM episodes")
        rows = cursor.fetchall()
        conn.close()

        if rows and query:
            query_vec = _get_embedding(query)
            scored = []
            for row in rows:
                input_text, feedback_text, emb_blob = row
                if emb_blob:
                    vec = _blob_to_vector(emb_blob)
                    sim = _cosine_similarity(query_vec, vec)
                    scored.append((sim, input_text, feedback_text))
            scored.sort(key=lambda x: x[0], reverse=True)
            top_episodes = scored[:MAX_EPISODES]
            if top_episodes:
                ep_strs = [
                    f"上次弹《{e[1]}》{e[2]}"
                    for e in top_episodes
                ]
                parts.append("【相似经历】" + "\n".join(ep_strs))
    except Exception as e:
        _log_cost(op="retrieve", detail=f"episodes_retrieve_error:{str(e)}")

    result = "\n".join(parts) if parts else ""
    _log_cost(op="retrieve", detail=f"retrieved:{len(parts)}_sections")
    return result


def distill(user_input: str, agent_output: str, user_feedback: str) -> None:
    """
    从用户反馈中提炼记忆，写入对应层。
    函数签名保持同步，调用方可在线程池中执行（主对话链路不等待）。
    """
    if not user_feedback or not user_feedback.strip():
        return

    result = _call_llm_for_distill(user_input, agent_output, user_feedback)
    if not result or result.get("type") == "none":
        return

    mem_type = result.get("type", "none")
    content = result.get("content", "")
    if not content:
        return

    try:
        if mem_type == "profile":
            profile = _load_profile()
            if ":" in content:
                key, val = content.split(":", 1)
                profile[key.strip()] = val.strip()
            else:
                profile["preference"] = content
            _save_profile(profile)
            _log_cost(op="distill", detail=f"profile_updated:{content}")

        elif mem_type == "rule":
            rules = _load_rules()
            new_vec = _get_embedding(content)
            duplicate = False
            for rule in rules:
                rule_text = rule.get("text", "")
                rule_vec = _get_embedding(rule_text)
                if _cosine_similarity(new_vec, rule_vec) >= 0.85:
                    rule["hit_count"] = rule.get("hit_count", 0) + 1
                    rule["created_at"] = datetime.now().isoformat()
                    duplicate = True
                    break
            if not duplicate:
                rules.append({
                    "id": int(time.time() * 1000),
                    "text": content,
                    "created_at": datetime.now().isoformat(),
                    "hit_count": 1
                })
            _save_rules(rules)
            _log_cost(op="distill", detail=f"rule_written:{content}")

        elif mem_type == "episode":
            vec = _get_embedding(content)
            conn = _get_conn()
            conn.execute(
                "INSERT INTO episodes (input, feedback, embedding, created_at) VALUES (?, ?, ?, ?)",
                (user_input, content, _vector_to_blob(vec), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            _log_cost(op="distill", detail=f"episode_written:{content}")

    except Exception as e:
        _log_cost(op="distill", detail=f"write_error:{str(e)}")


def get_memory_snapshot() -> dict:
    """返回三层记忆当前完整内容 + 累计成本统计"""
    snapshot = {
        "profile": {},
        "rules": [],
        "episodes_count": 0,
        "cost": {
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_latency_ms": 0.0,
            "memory_ops": 0
        }
    }

    # 画像层
    try:
        snapshot["profile"] = _load_profile()
    except Exception:
        pass

    # 规则层
    try:
        snapshot["rules"] = _load_rules()
    except Exception:
        pass

    # 情景层计数
    try:
        conn = _get_conn()
        cursor = conn.execute("SELECT COUNT(*) FROM episodes")
        row = cursor.fetchone()
        snapshot["episodes_count"] = row[0] if row else 0
        conn.close()
    except Exception:
        pass

    # 从 memory_log.jsonl 汇总成本
    try:
        if LOG_PATH.exists():
            total_in = 0
            total_out = 0
            total_lat = 0.0
            ops = 0
            with open(LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        total_in += entry.get("tokens_in", 0)
                        total_out += entry.get("tokens_out", 0)
                        total_lat += entry.get("latency_ms", 0)
                        ops += 1
                    except Exception:
                        continue
            snapshot["cost"]["total_tokens_in"] = total_in
            snapshot["cost"]["total_tokens_out"] = total_out
            snapshot["cost"]["total_latency_ms"] = round(total_lat, 2)
            snapshot["cost"]["memory_ops"] = ops
    except Exception:
        pass

    # 记忆总条数
    snapshot["cost"]["memory_count"] = (
        len(snapshot.get("profile", {})) +
        len(snapshot.get("rules", [])) +
        snapshot.get("episodes_count", 0)
    )

    return snapshot
