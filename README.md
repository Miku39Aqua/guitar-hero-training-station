# 吉他英雄训练站

ACG 吉他练琴 Agent。输入歌名或上传音频，自动生成适配你当前水平的六线谱，并持续记忆你的偏好与痛点。

## 环境要求

- Python 3.11+
- Windows / macOS / Linux
- 推荐 8GB+ 内存（Demucs htdemucs_6s 模型约 1.8GB）

## 一键启动

```bash
# 1. 克隆仓库
git clone https://github.com/Miku39Aqua/guitar-hero-training-station.git
cd guitar-hero-training-station

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 DeepSeek API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY

# 4. 启动服务端
python server.py

# 5. 浏览器打开
http://localhost:8000
```

## 核心功能

- **对话生成谱面**：输入歌名，Agent 自动生成六线谱
- **音频扒谱**：上传 MP3/WAV，Demucs 分离吉他 + basic-pitch 音高检测 → 六线谱
- **意外选曲**：点击「🎲 给我来点没听过的」，推荐风格距离最大且技术匹配的曲子
- **记忆系统**：三层记忆（画像 / 规则 / 情景），持续优化推荐
- **音色推荐**：根据曲子风格推荐吉他音色配置
- **GP5 导出**：生成谱面后可下载 Guitar Pro 5 格式文件
- **历史记录**：自动记录生成过的谱面，可回看

## 项目结构

```
audio/              # 音频管线（Demucs + basic-pitch + 指法引擎）
tab_engine/         # 谱面引擎（IR + 改编 + alphaTex + GP5 导出）
agent/              # Agent 记忆系统
features/           # 35+ 首曲子风格特征库
web/                # 前端（对话 + 谱面区 + 记忆面板）
server.py           # FastAPI 服务端
```

## 技术栈

- Python 3.11 / FastAPI
- Demucs（音乐源分离）
- basic-pitch（音高检测）
- PyGuitarPro + alphaTab（谱面渲染）
- DeepSeek LLM（对话生成）


