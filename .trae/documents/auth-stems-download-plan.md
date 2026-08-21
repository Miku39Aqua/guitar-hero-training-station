# 用户认证、个人历史与多轨分离下载实现计划

## Context

为现有「吉他英雄训练站」网页增加一套完整的用户系统与音乐分轨下载功能。现有系统已支持：上传音频 → Demucs 分离吉他 → basic-pitch → 生成吉他谱（alphaTex）。本次新增需求包括：

1. 用户注册/登录/记住我/安全密码存储（暂时不做邮件重置）。
2. 登录用户可查看自己的音频处理历史；未登录用户仍可完整使用核心功能。
3. 独立的「分轨纯享」功能：选择多个乐器分轨，系统返回所选分轨及排除后的混音轨道。
4. 打包下载所选轨道，支持进度显示与断点续传。

## 设计决策（基于用户确认）

* **历史记录**：保留现有公共/匿名历史，新增登录用户的「我的历史」。

* **忘记密码**：本阶段不实现，后续可扩展。

* **多轨功能**：作为独立入口，不强制绑定吉他谱生成流程。

* **数据库**：复用 SQLite，新建 `data/auth_history.db`。

* **认证方式**：JWT + Bearer Header，「记住我」通过延长 token 有效期实现。

## 数据库 Schema（data/auth\_history.db）

```sql
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT NOT NULL UNIQUE,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS extraction_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,                 -- NULL 表示匿名
    task_id         TEXT NOT NULL UNIQUE,
    filename        TEXT NOT NULL,           -- 原始上传文件名
    source          TEXT,                    -- stems / audio / llm / builtin
    extraction_type TEXT,                    -- 多轨选择 JSON，如 ["guitar","piano"]
    status          TEXT DEFAULT 'pending',
    progress        TEXT,
    zip_path        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    completed_at    TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_history_user_created ON extraction_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_task ON extraction_history(task_id);
```

## 后端实现

### 新增依赖

更新 `requirements.txt`：

```text
python-jose[cryptography]
passlib[bcrypt]
python-multipart
email-validator
```

### 新增模块

| 文件                            | 职责                                                                       |
| ----------------------------- | ------------------------------------------------------------------------ |
| `auth/db.py`                  | SQLite 连接、用户 CRUD、历史记录 CRUD、建表迁移                                         |
| `auth/security.py`            | bcrypt 密码哈希、JWT 生成/解码、当前用户依赖 `get_current_user`                          |
| `auth/router.py`              | `/api/auth/register`、`/api/auth/login`、`/api/auth/me`、`/api/auth/logout` |
| `services/package_service.py` | zip 打包、剩余轨道混音                                                            |
| `services/range_response.py`  | 支持 `Range` 头的文件下载                                                        |

### 关键 API 变更

* **POST** **`/api/auth/register`**：注册，密码 bcrypt 哈希。

* **POST** **`/api/auth/login`**：登录，返回 JWT；`remember_me=true` 时 token 有效期 7 天，否则 2 小时。

* **GET** **`/api/auth/me`**：返回当前登录用户信息。

* **POST** **`/api/auth/logout`**：客户端清除 token，后端无状态。

* **POST** **`/api/upload`**：保持不变，但可选接收 `Authorization` Header 记录用户 ID。

* **POST** **`/api/chat`**：保持不变；音频转谱流程仍为现有功能。

* **新增 POST** **`/api/separate`**：独立分轨入口。

  * 请求：`{ audio_filename, selected_stems: ["guitar","piano",...] }`

  * 返回：`{ task_id }`

* **新增 GET** **`/api/tasks/{task_id}/download`**：下载 zip，支持 `Range`。

* **GET** **`/api/history`**：原公共历史保留；新增登录用户时返回个人历史（分页）。

* **新增 GET** **`/api/me/history`**：当前登录用户专属历史（分页、按时间排序）。

### Demucs 多轨分离改造

修改 `audio/demucs_runner.py`：

1. 新增 `separate_stems(audio_path, output_dir, selected_stems=None)`。
2. 去掉 `--two-stems`，调用完整 6 轨：`vocals`、`drums`、`bass`、`guitar`、`piano`、`other`。
3. 对 `selected_stems` 中的每个轨道，直接读取对应 `.wav`。
4. 生成排除混音 `no_<stem1>_<stem2>.wav`：将剩余轨道用 `soundfile`+`numpy` 叠加并防削波。
5. 返回字典：`{ "guitar": path, "piano": path, "no_guitar_piano": path, ... }`。

### 任务流程

新增 `run_separate_task(task_id, audio_filename, selected_stems, user_id)`：

1. 写入 `extraction_history` 占位记录。
2. Demucs 全部分离。
3. 生成排除混音。
4. zip 打包到 `exports/{task_id}.zip`。
5. 更新任务状态为 done，返回 `zip_url` 与 `zip_size`。

### 安全

* 密码：bcrypt，12 rounds。

* JWT：`JWT_SECRET` 从 `.env` 读取；token 不过长。

* 文件访问：所有路径基于 `PROJECT_ROOT`，禁止 `..`；下载接口校验任务所有者或匿名公开。

* SQL：参数化查询。

* 上传：限制大小 50MB，校验 `audio/*`。

### 缓存

* 文件级缓存：以原文件 SHA-256 为键，保存 Demucs 输出到 `uploads/cache/<hash>/`。

* zip 缓存：按 `task_id` 命名，避免重复打包。

* 缓存清理：启动时删除 7 天未访问的缓存目录。

## 前端实现

### 新增 UI

* **顶部用户信息条**：`.panel-header` 右侧，显示「登录/注册」或「用户名 + 退出」。

* **登录/注册弹窗**：居中 modal，含 tab 切换。

* **分轨纯享入口**：在对话区新增「分轨下载」按钮，点击后选择文件、选择轨道、提交处理。

* **轨道选择面板**：6 个复选框（吉他、钢琴、贝斯、鼓、人声、其他）+ 全选/清空 + 确认。

* **下载区域**：任务完成后显示 zip 下载按钮、文件大小、处理耗时。

* **我的历史**：历史记录区新增「我的历史」标签页，分页展示。

### 修改文件

* `web/index.html`：用户信息条、登录 modal、分轨选择面板。

* `web/style.css`：modal、轨道选择器、下载按钮、用户条样式。

* `web/app.js`：

  * `AuthManager`：token 管理、登录态渲染、自动附加 `Authorization`。

  * 分轨流程：选择文件 → 选择轨道 → POST `/api/separate` → 轮询 → 显示下载。

  * 轮询逻辑：任务 done 且有 `zip_url` 时渲染下载按钮。

  * 我的历史：分页加载 `/api/me/history`。

## 关键文件清单

* `server.py`：注册 auth 路由、新增 `/api/separate`、下载端点、任务流程。

* `auth/db.py`、`auth/security.py`、`auth/router.py`：认证与持久化。

* `services/package_service.py`、`services/range_response.py`：打包与下载。

* `audio/demucs_runner.py`：多轨分离与排除混音。

* `web/index.html`、`web/style.css`、`web/app.js`：前端交互。

* `requirements.txt`、`.env.example`：依赖与配置模板。

## 验证步骤

1. 安装依赖并配置 `.env`（`JWT_SECRET`）。
2. 启动服务，确认 `data/auth_history.db` 自动建表。
3. 注册、登录、`/api/auth/me` 返回正确信息。
4. 未登录上传音频，确认仍可生成吉他谱。
5. 登录后使用「分轨下载」：选择 guitar + piano，确认任务完成。
6. 检查 `uploads/demucs_output/...` 下有 `guitar.wav`、`piano.wav`、`no_guitar_piano.wav`。
7. 下载 zip，内部文件名正确；用 `curl -H "Range: bytes=0-1023"` 测试 206。
8. 我的历史分页正常，按时间倒序。
9. 同一文件再次上传，Demucs 从缓存复用。
10. 尝试越权下载他人任务，返回 403。

