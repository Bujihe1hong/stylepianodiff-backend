# StylePianoDiff Web 平台 - 后端部署说明

## 项目简介

StylePianoDiff Web 平台后端，基于 **FastAPI** + **SQLAlchemy** 构建，提供风格化钢琴片段生成的 RESTful API 服务。

后端通过 `subprocess` 调用核心模型项目 (`stylepianodiff`) 的 `scripts/sample.py` 进行推理，不修改模型代码。

---

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 运行环境 |
| FastAPI | 0.111.0 | Web 框架 |
| Uvicorn | 0.30.0 | ASGI 服务器 |
| SQLAlchemy | 2.0.31 | ORM |
| pyodbc | 5.1.0 | SQL Server 连接驱动 |
| Pydantic | 2.7.4 | 数据校验 |
| pydantic-settings | 2.3.4 | 配置管理 |
| python-jose | 3.3.0 | JWT 认证 |
| passlib | 1.7.4 | 密码哈希 |
| python-multipart | 0.0.9 | 文件上传 |
| aiofiles | 23.2.1 | 异步文件操作 |
| pretty_midi | - | MIDI 解析 |

---

## 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── api/
│   │   ├── __init__.py         # 路由聚合 (api_router)
│   │   ├── composers.py        # 作曲家风格 API
│   │   ├── generate.py         # 生成任务 API
│   │   ├── history.py          # 生成历史 API
│   │   ├── midi.py             # MIDI 文件 API
│   │   └── users.py            # 用户认证 API
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings 配置（主配置）
│   │   ├── database.py         # SQLAlchemy 引擎与 Session
│   │   └── security.py         # JWT 与密码工具
│   ├── models/
│   │   ├── __init__.py
│   │   ├── composer_style.py   # 作曲家风格 ORM
│   │   ├── generation_history.py
│   │   ├── generation_job.py   # 生成任务 ORM
│   │   ├── midi_file.py        # MIDI 文件 ORM
│   │   ├── model_checkpoint.py
│   │   └── user.py             # 用户 ORM
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── composer_style.py
│   │   ├── generation_job.py
│   │   ├── midi_file.py
│   │   └── user.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── generation_service.py  # 模型推理服务封装
│   ├── utils/
│   │   ├── __init__.py
│   │   └── midi_parser.py      # MIDI 解析为钢琴卷帘 JSON
│   └── worker.py               # 后台任务 Worker（threading）
├── uploads/                    # 上传的 MIDI 种子文件
├── generated/                  # 生成结果 MIDI 文件
├── sql/
│   └── init_database.sql       # 数据库初始化脚本（SQL Server）
├── requirements.txt            # Python 依赖
├── .env                        # 环境变量（从 .env.example 复制）
├── .env.example                # 环境变量模板
└── README.md                   # 本文件
```

---

## 环境准备

### 1. 安装 Python 依赖

```bash
cd D:\pycharm\stylepianodiff-web\backend

# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，并根据本地环境修改：

```bash
copy .env.example .env
```

关键配置项：

| 变量 | 说明 | 示例 |
|------|------|------|
| `DATABASE_URL` | SQLAlchemy 连接字符串 | `mssql+pyodbc://sa:密码@localhost/StylePianoDB?driver=ODBC+Driver+17+for+SQL+Server` |
| `SECRET_KEY` | JWT 签名密钥 | `your-secret-key` |
| `MODEL_PROJECT_PATH` | 核心模型项目路径 | `D:\pycharm\stylepianodiff` |
| `CHECKPOINT_PATH` | 模型 checkpoint 路径 | `D:\pycharm\stylepianodiff\outputs\diffusion\stage3_best.pt` |
| `UPLOAD_DIR` | 上传文件保存目录 | `D:\pycharm\stylepianodiff-web\backend\uploads` |
| `GENERATED_DIR` | 生成结果保存目录 | `D:\pycharm\stylepianodiff-web\backend\generated` |

### 3. 初始化数据库

确保 SQL Server 已安装并运行，然后执行初始化脚本：

```bash
# 使用 sqlcmd 执行（需安装 SQL Server 命令行工具）
sqlcmd -S localhost -d master -i sql\init_database.sql

# 或使用 SSMS 打开脚本执行
```

脚本将创建：
- 数据库 `StylePianoDB`
- 6 张数据表（users, composer_styles, midi_files, generation_jobs, generation_history, model_checkpoints）
- 索引、触发器、存储过程、视图
- 默认作曲家风格数据（Bach, Mozart, Beethoven, Chopin, Debussy, Liszt）

---

## 启动服务

### 方式一：使用一键启动脚本（推荐）

在项目根目录执行：

```bash
D:\pycharm\stylepianodiff-web\start.bat
```

脚本将自动：
1. 检查并启动 SQL Server 服务
2. 检查模型文件是否存在
3. 启动 FastAPI 后端（新窗口）
4. 启动 Vue 前端（新窗口）
5. 等待 5 秒后自动打开浏览器

### 方式二：手动启动后端

```bash
cd D:\pycharm\stylepianodiff-web\backend
.venv\Scripts\activate.bat
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式三：直接运行 main.py

```bash
cd D:\pycharm\stylepianodiff-web\backend
.venv\Scripts\activate.bat
python app\main.py
```

---

## API 接口说明

### 生成任务相关

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate/submit` | 提交生成任务（上传 MIDI + 参数） |
| GET | `/api/generate/status/{job_id}` | 查询任务状态 |
| GET | `/api/generate/download/{job_id}` | 下载生成结果 MIDI |
| GET | `/api/generate/preview/{job_id}` | 获取生成结果钢琴卷帘预览 JSON |
| GET | `/api/generate/list` | 获取用户生成任务列表 |

### 系统接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

### 其他已有接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/users/register` | 用户注册 |
| POST | `/api/users/login` | 用户登录 |
| GET | `/api/users/me` | 获取当前用户 |
| GET | `/api/composers` | 作曲家风格列表 |
| GET | `/api/composers/{id}` | 作曲家详情 |
| POST | `/api/midi/upload` | 上传 MIDI 文件 |
| GET | `/api/midi/{file_id}` | 下载 MIDI 文件 |
| GET | `/api/midi` | MIDI 文件列表 |
| GET | `/api/history` | 生成历史列表 |
| PUT | `/api/history/{id}/favorite` | 切换收藏 |
| PUT | `/api/history/{id}/rating` | 评分 |

---

## 生成任务流程

```
前端上传 MIDI 文件
       ↓
POST /api/generate/submit
       ↓
保存文件 → 创建 midi_files 记录 → 创建 generation_jobs 记录 (pending)
       ↓
启动 FastAPI BackgroundTasks + threading 后台线程
       ↓
调用 generation_service.run_generation()
       ↓
构建命令行 → subprocess 执行 sample.py
       ↓
更新数据库状态 (running → done / failed)
       ↓
前端轮询 /api/generate/status/{job_id}
       ↓
状态为 done → 调用 /api/generate/preview 或 /api/generate/download
```

---

## 模型推理参数映射

| Web 参数 | sample.py 参数 | 说明 |
|----------|----------------|------|
| `seed_file` | `--seed` | 种子 MIDI 文件路径 |
| `composer_name` | `--style` | 作曲家风格名称 |
| `alpha` | `--alpha` | 风格强度 |
| `temperature` | - | 采样温度（预留，如 sample.py 支持则传入） |
| `target_bars` | - | 目标小节数（预留，如 sample.py 支持则传入） |

---

## 常见问题

### 1. ODBC Driver 17 未安装

下载并安装 Microsoft ODBC Driver 17 for SQL Server：
https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

### 2. SQL Server 连接失败

- 确认 SQL Server 服务已启动（`services.msc` 中检查 `SQL Server (MSSQLSERVER)`）
- 确认 TCP/IP 协议已启用（SQL Server 配置管理器）
- 确认防火墙允许 1433 端口
- 检查 `DATABASE_URL` 中的用户名和密码是否正确

### 3. 模型 checkpoint 不存在

训练完成后将 `stage3_best.pt` 放置到 `D:\pycharm\stylepianodiff\outputs\diffusion\` 目录，或在 `.env` 中修改 `CHECKPOINT_PATH`。

### 4. pretty_midi 安装失败

pretty_midi 依赖 `mido`，如安装失败可尝试：

```bash
pip install mido pretty_midi
```

### 5. 生成超时

在 `.env` 中调整 `GENERATION_TIMEOUT`（默认 120 秒）。

---

## 开发注意事项

1. **不修改模型代码**：所有模型调用通过 `subprocess` 执行 `sample.py`，保持模型项目独立
2. **Windows 路径**：所有路径使用 `pathlib.Path` 或原始字符串（`r"D:\..."`），避免转义问题
3. **后台任务**：使用 `threading` + `FastAPI BackgroundTasks`，不引入 Celery 降低复杂度
4. **错误处理**：任何步骤失败都会更新数据库状态为 `failed` 并记录错误信息
5. **文件存储**：上传文件和生成结果均保存到磁盘，数据库只存储路径和元数据
6. **ORM 使用**：数据库操作统一使用 SQLAlchemy ORM，通过 `get_db()` 依赖注入 Session

---

## 联系方式

如有问题，请参考核心模型项目 `D:\pycharm\stylepianodiff\README.md` 或联系开发团队。
