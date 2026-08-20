"""吉他英雄训练站服务端

真实集成：LLM 对话 + 记忆系统 + 改编引擎 + alphaTex 转换
支持后台任务 + 前端轮询
"""
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from collections import defaultdict

# 加载 .env 文件
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tab_engine.ir import ScoreIR, MeasureIR, BeatIR, NoteIR
from tab_engine.adapt import adapt_difficulty
from tab_engine.to_alphatex import score_to_alphatex_compact

import agent.memory as memory
from features.surprise import surprise_me

app = FastAPI(title="吉他英雄训练站")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 后台任务存储 ==========

class Task:
    def __init__(self):
        self.status = "pending"  # pending / running / done / failed
        self.progress = ""       # 进度描述
        self.result = None       # ChatResponse
        self.error = None
        self.created_at = time.time()

_task_store: dict[str, Task] = {}


# ========== 历史记录存储 ==========

class HistoryItem:
    def __init__(self, title: str, artist: str, alphatex: str, reply: str, source: str = ""):
        self.id = uuid.uuid4().hex
        self.title = title
        self.artist = artist
        self.alphatex = alphatex
        self.reply = reply
        self.source = source
        self.created_at = time.time()

_history_store: list[HistoryItem] = []
_HISTORY_MAX = 50


def add_history(title: str, artist: str, alphatex: str, reply: str, source: str = "") -> HistoryItem:
    item = HistoryItem(title=title, artist=artist, alphatex=alphatex, reply=reply, source=source)
    _history_store.insert(0, item)
    if len(_history_store) > _HISTORY_MAX:
        _history_store = _history_store[:_HISTORY_MAX]
    return item


def get_history() -> list[dict]:
    return [
        {
            "id": item.id,
            "title": item.title,
            "artist": item.artist,
            "source": item.source,
            "created_at": item.created_at,
        }
        for item in _history_store
    ]


def get_history_item(item_id: str) -> dict | None:
    for item in _history_store:
        if item.id == item_id:
            return {
                "id": item.id,
                "title": item.title,
                "artist": item.artist,
                "alphatex": item.alphatex,
                "reply": item.reply,
                "source": item.source,
                "created_at": item.created_at,
            }
    return None


def get_task(task_id: str) -> Task | None:
    return _task_store.get(task_id)


# ========== LLM 客户端 ==========

def get_llm_client():
    base_url = os.getenv("LLM_BASE_URL", "")
    api_key = os.getenv("LLM_API_KEY", "")
    if not base_url or not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(base_url=base_url, api_key=api_key, timeout=300)
    except Exception:
        return None


def suggest_tone(title: str, artist: str, bpm: int, style_vector: dict, techniques: list, difficulty: int) -> dict:
    """根据歌曲特征推荐吉他音色设置（规则引擎版）"""
    style = ""
    if style_vector:
        style = max(style_vector, key=style_vector.get)

    # 默认
    guitar = "电吉他"
    preset = "Clean"
    amp = "Fender Twin"
    effects = []
    description = "标准 Clean 音色，适合流行/民谣"

    # ACG
    if style == "ACG" or (style_vector.get("ACG", 0) > 0.6):
        guitar = "电吉他"
        preset = "Clean + 轻微合唱"
        amp = "Roland JC-120"
        effects = ["合唱 Chorus", "延迟 Delay(100ms)"]
        description = "清亮脆爽的 ACG 标配音色，带一点空间感"

    # 摇滚
    if style == "摇滚" or (style_vector.get("摇滚", 0) > 0.6):
        preset = "Crunch"
        amp = "Marshall JCM800"
        effects = ["延迟 Delay", "混响 Reverb"]
        description = "经典摇滚 Crunch，中频突出，带一点失真"

    # 金属
    if style == "金属" or (style_vector.get("金属", 0) > 0.6) or (difficulty >= 4 and "强力和弦" in techniques):
        preset = "High Gain"
        amp = "Mesa Boogie Dual Rectifier"
        effects = ["噪声门 Noise Gate"]
        description = "高增益金属音色， tight 的低频，适合强力和弦"

    # 爵士
    if style == "爵士" or (style_vector.get("爵士", 0) > 0.6):
        guitar = "半空心吉他"
        preset = "Jazz Clean"
        amp = "Polytone"
        effects = ["混响 Reverb(轻)"]
        description = "温暖圆润的爵士 Clean，适合和弦与walking bass"

    # 民谣
    if style == "民谣" or (style_vector.get("民谣", 0) > 0.6):
        guitar = "原声吉他"
        preset = "Acoustic"
        amp = "直接输出 DI"
        effects = ["混响 Reverb( hall )"]
        description = "原声吉他直接录音， hall 混响增加空间感"

    # BPM 修正
    if bpm >= 160 and preset == "Clean":
        preset = "Clean + 轻微过载"
        effects.append("过载 Overdrive(轻)")
        description += "；BPM 较快，加一点过驱增加推力和弦的饱满度"

    return {
        "guitar": guitar,
        "preset": preset,
        "amp": amp,
        "effects": effects,
        "description": description,
    }


def call_llm_for_song(message: str, memory_context: str, on_progress=None) -> dict:
    """调用 LLM 生成谱面。返回 dict 或 None"""
    client = get_llm_client()
    if not client:
        return None

    model = os.getenv("LLM_MODEL", "deepseek-v4-flash")

    prompt = f"""你是 ACG 吉他谱生成助手。用户输入一首曲子名，你根据原曲的真实旋律特征，生成完整的吉他谱（主音旋律 + 节奏和弦）。

{memory_context}

用户想弹：{message}

请回忆原曲的真实旋律特征：
- 原曲的典型 BPM 是多少？（必须准确）
- 主歌部分有什么标志性旋律？（用简谱描述：1 1 2 3 | 3 2 1 - |）
- 副歌部分有什么记忆点？
- 原曲是主音吉他主导还是节奏吉他主导？

输出 JSON：
{{
    "title": "曲名",
    "artist": "艺术家",
    "bpm": 原曲真实BPM数值,
    "style": "主音/节奏/双吉他",
    "parts": [
        {{"role": "lead", "instrument": "主音吉他", "description": "主旋律", "measures": [...]}},
        {{"role": "rhythm", "instrument": "节奏吉他", "description": "和弦伴奏", "measures": [...]}}
    ]
}}
其中 measures 是数组，每个元素：
{{"beats": [{{"duration": 4, "notes": [{{"string": 3, "fret": 0}}]}}, ...]}}

规则：
- 尽量还原原曲真实旋律，不要瞎编
- BPM 必须准确（God Knows=172, only my railgun=143, secret base=87）
- 每个小节恰好 4 个 beat
- duration: 4=四分, 8=八分, 2=二分, 16=十六分
- string: 1-6（1=高音e弦）
- fret: 0-15
- 只输出 JSON，不要解释
"""

    if on_progress:
        on_progress("已发送 prompt 给 LLM，等待生成...")

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            timeout=300,
        )
        content = (resp.choices[0].message.content or "").strip()
        finish_reason = resp.choices[0].finish_reason

        import json
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            print(f"LLM call failed: no JSON (finish={finish_reason}, len={len(content)})")
            return None
        return json.loads(content[start:end + 1])
    except Exception as e:
        print(f"LLM call failed: {e}")
        return None


# ========== 谱面生成 ==========

def build_demo_song(song_name: str) -> ScoreIR:
    demos = {
        "god knows": ScoreIR(title="God Knows", artist="凉宫春日的忧郁", bpm=172),
        "only my railgun": ScoreIR(title="Only My Railgun", artist="某科学的超电磁炮", bpm=143),
        "secret base": ScoreIR(title="secret base", artist="未闻花名", bpm=87),
    }
    key = song_name.lower().strip()
    matched = None
    for demo_key in demos:
        if demo_key in key:
            matched = demo_key
            break

    if matched:
        ir = demos[matched]
    else:
        ir = ScoreIR(title=song_name, artist="", bpm=120)

    if not ir.measures:
        for _ in range(4):
            m = MeasureIR(beats=[
                BeatIR(duration=4, notes=[NoteIR(string=3, fret=0)]),
                BeatIR(duration=4, notes=[NoteIR(string=3, fret=2)]),
                BeatIR(duration=4, notes=[NoteIR(string=2, fret=0)]),
                BeatIR(duration=4, notes=[NoteIR(string=2, fret=1)]),
            ])
            ir.measures.append(m)

    return ir


def generate_score_from_llm(llm_data: dict) -> ScoreIR | None:
    """将 LLM 返回的 JSON 转为 ScoreIR（支持多声部）"""
    try:
        title = llm_data.get("title", "Untitled")
        artist = llm_data.get("artist", "")
        bpm = llm_data.get("bpm", 120)

        # 如果有 parts（多声部），合并为一个 ScoreIR（主音优先）
        parts = llm_data.get("parts", [])
        if parts:
            lead_part = next((p for p in parts if p.get("role") == "lead"), parts[0])
            ir = ScoreIR(title=title, artist=artist, bpm=bpm)
            for m_data in lead_part.get("measures", []):
                m = MeasureIR()
                for b_data in m_data.get("beats", []):
                    beat = BeatIR(duration=b_data.get("duration", 4))
                    for n_data in b_data.get("notes", []):
                        beat.notes.append(NoteIR(
                            string=n_data.get("string", 3),
                            fret=n_data.get("fret", 0),
                        ))
                    m.beats.append(beat)
                ir.measures.append(m)
            return ir
        else:
            # 兼容旧格式（单声部 measures）
            ir = ScoreIR(title=title, artist=artist, bpm=bpm)
            for m_data in llm_data.get("measures", []):
                m = MeasureIR()
                for b_data in m_data.get("beats", []):
                    beat = BeatIR(duration=b_data.get("duration", 4))
                    for n_data in b_data.get("notes", []):
                        beat.notes.append(NoteIR(
                            string=n_data.get("string", 3),
                            fret=n_data.get("fret", 0),
                        ))
                    m.beats.append(beat)
                ir.measures.append(m)
            return ir
    except Exception as e:
        print(f"LLM result parse failed: {e}")
        return None


# ========== 后台任务执行 ==========

def run_chat_task(task_id: str, message: str, audio_filename: str | None = None):
    task = get_task(task_id)
    if not task:
        return

    try:
        task.status = "running"

        # 1. 如果有音频文件，走音频管线
        if audio_filename:
            task.progress = "正在处理音频（音频管线尚未接入模型，当前为演示模式）..."
            audio_path = Path("uploads") / audio_filename
            if audio_path.exists():
                from audio import transcribe_audio
                ir = transcribe_audio(str(audio_path), progress_callback=lambda s: setattr(task, "progress", s))
                source = "audio"
            else:
                ir = build_demo_song(message or audio_filename)
                source = "builtin"
        else:
            # 纯文字对话
            task.progress = "正在检索记忆..."

            memory_context = memory.retrieve(message)

            task.progress = "记忆检索完成，正在生成谱面（AI 生成中，可能需要 1-2 分钟）..."

            def on_progress(msg):
                task.progress = msg

            llm_result = call_llm_for_song(message, memory_context, on_progress=on_progress)

            if llm_result and ("measures" in llm_result or "parts" in llm_result):
                ir = generate_score_from_llm(llm_result)
                source = "llm"
            else:
                ir = build_demo_song(message)
                source = "builtin"

        task.progress = "谱面生成完成，正在应用改编规则..."

        # 2. 改编
        profile = memory._load_profile()
        adapted_ir, report = adapt_difficulty(ir, profile)

        # 3. 转 alphaTex
        task.progress = "正在渲染谱面..."
        alphatex = score_to_alphatex_compact(adapted_ir)

        # 4. 构建回复
        source_tag = {
            "llm": "AI 生成",
            "builtin": "内置演示",
            "audio": "音频转写",
        }.get(source, "生成")
        reply = f"已为你生成《{ir.title}》的吉他谱（{source_tag}）。"
        if report.changes:
            reply += f"\n\n{report.summary_text()}"
        user_input = message or (audio_filename or "")
        memory_context = memory.retrieve(user_input)
        if memory_context:
            reply += f"\n\n（已参考你的历史偏好）"

        task.progress = "完成"
        task.status = "done"
        task.result = {"reply": reply, "alphatex": alphatex}

        # 保存到历史记录
        add_history(
            title=ir.title,
            artist=ir.artist,
            alphatex=alphatex,
            reply=reply,
            source=source,
        )

        # 5. 异步 distill
        def do_distill():
            memory.distill(
                user_input=user_input,
                agent_output=reply,
                user_feedback="",
            )
        threading.Thread(target=do_distill, daemon=True).start()

    except Exception as e:
        task.status = "failed"
        task.error = str(e)
        task.progress = f"失败: {e}"


# ========== API 路由 ==========

class ChatRequest(BaseModel):
    message: str
    audio_filename: str | None = None  # 前端先上传到 /api/upload，拿到文件名再发 chat


class ChatResponse(BaseModel):
    reply: str
    alphatex: str


class MemoryResponse(BaseModel):
    profile: dict
    rules: list
    episodes_count: int
    cost: dict


@app.get("/")
async def root():
    return FileResponse("web/index.html")


@app.post("/api/chat")
async def chat(req: ChatRequest):
    message = req.message.strip()
    if not message and not req.audio_filename:
        return ChatResponse(reply="请告诉我你想弹什么曲子，或上传一段音频。", alphatex="")

    task_id = uuid.uuid4().hex
    task = Task()
    _task_store[task_id] = task

    threading.Thread(
        target=run_chat_task,
        args=(task_id, message, req.audio_filename),
        daemon=True,
    ).start()

    return {"task_id": task_id}


@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """上传音频文件，返回可访问的文件名。"""
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    return {"filename": file.filename}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        return {"error": "task not found"}, 404

    resp = {
        "status": task.status,
        "progress": task.progress,
    }
    if task.status == "done" and task.result:
        resp["reply"] = task.result["reply"]
        resp["alphatex"] = task.result["alphatex"]
    if task.status == "failed":
        resp["error"] = task.error
    return resp


@app.get("/api/memory", response_model=MemoryResponse)
async def get_memory():
    snapshot = memory.get_memory_snapshot()
    return MemoryResponse(
        profile=snapshot["profile"],
        rules=snapshot["rules"],
        episodes_count=snapshot["episodes_count"],
        cost=snapshot["cost"],
    )


class SurpriseResponse(BaseModel):
    title: str
    artist: str
    surprise_score: float
    reason: str
    features: dict


@app.get("/api/surprise-me", response_model=SurpriseResponse)
async def surprise_me_api():
    item = surprise_me()
    if not item:
        return SurpriseResponse(
            title="无推荐",
            artist="",
            surprise_score=0.0,
            reason="特征库为空",
            features={},
        )
    return SurpriseResponse(**item)


@app.get("/api/history")
async def get_history_api():
    return get_history()


@app.get("/api/history/{item_id}")
async def get_history_item_api(item_id: str):
    item = get_history_item(item_id)
    if not item:
        return {"error": "not found"}, 404
    return item


class ToneRequest(BaseModel):
    title: str
    artist: str = ""
    bpm: int = 120
    style_vector: dict = {}
    techniques: list = []
    difficulty: int = 3


class ToneResponse(BaseModel):
    guitar: str
    preset: str
    amp: str
    effects: list
    description: str


@app.post("/api/suggest-tone", response_model=ToneResponse)
async def suggest_tone_api(req: ToneRequest):
    result = suggest_tone(
        title=req.title,
        artist=req.artist,
        bpm=req.bpm,
        style_vector=req.style_vector,
        techniques=req.techniques,
        difficulty=req.difficulty,
    )
    return ToneResponse(**result)


# 静态文件挂载
app.mount("/", StaticFiles(directory="web", html=True), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
