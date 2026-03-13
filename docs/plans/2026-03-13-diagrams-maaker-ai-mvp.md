# diagrams.maaker.ai MVP 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 maaker.ai 上新增 /diagrams 页面，用户输入文字描述或 Mermaid 代码，生成手绘风 Excalidraw 图表，支持预览和下载。

**Architecture:** 前端是纯 HTML + Tailwind（与 index.html 一致），通过 fetch 调用部署在 1.15.12.53 的 Python API。API 是一层薄 FastAPI wrapper，直接调用 excalidraw-mcp 引擎的核心函数生成图表，返回 Excalidraw JSON + SVG。

**Tech Stack:** HTML + Tailwind CDN（前端）、FastAPI + uvicorn（API）、excalidraw-mcp 引擎（Python）、Docker（部署）、Cloudflare Pages（前端托管）

---

## Task 1: Python API 服务

**目标：** 创建一个 FastAPI 服务，包装 excalidraw-mcp 引擎的 5 种图表生成能力，暴露 HTTP 接口。

**Files:**
- Create: `api/main.py` — FastAPI 入口
- Create: `api/requirements.txt` — 依赖
- Create: `api/Dockerfile` — 容器化

**Step 1: 创建 API 目录和依赖文件**

```
api/requirements.txt:
fastapi>=0.115.0
uvicorn>=0.34.0
maaker-excalidraw-mcp>=0.5.1
```

**Step 2: 写 FastAPI 主文件**

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json, tempfile, os

app = FastAPI(title="Diagrams API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://maaker.ai", "https://diagrams.maaker.ai", "http://localhost:8080"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# --- Import excalidraw-mcp engine ---
from excalidraw_mcp.tools.flowchart import create_flowchart_impl
from excalidraw_mcp.tools.architecture import create_architecture_impl
from excalidraw_mcp.tools.sequence import create_sequence_impl
from excalidraw_mcp.tools.mindmap import create_mindmap_impl
from excalidraw_mcp.tools.mermaid import import_mermaid_impl
from excalidraw_mcp.utils.svg_export import export_to_svg

# --- Request Models ---
class DiagramRequest(BaseModel):
    type: str  # flowchart | architecture | sequence | mindmap | mermaid
    data: dict
    title: Optional[str] = None
    theme: str = "light"

# --- API Endpoint ---
@app.post("/api/generate")
async def generate_diagram(req: DiagramRequest):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "diagram.excalidraw")

            if req.type == "flowchart":
                create_flowchart_impl(
                    nodes=req.data.get("nodes", []),
                    edges=req.data.get("edges", []),
                    direction=req.data.get("direction", "LR"),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "architecture":
                create_architecture_impl(
                    layers=req.data.get("layers", []),
                    connections=req.data.get("connections", []),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "sequence":
                create_sequence_impl(
                    participants=req.data.get("participants", []),
                    messages=req.data.get("messages", []),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mindmap":
                create_mindmap_impl(
                    root=req.data.get("root", {}),
                    title=req.title,
                    output_path=output_path,
                    theme=req.theme,
                )
            elif req.type == "mermaid":
                import_mermaid_impl(
                    mermaid=req.data.get("mermaid", ""),
                    output_path=output_path,
                    theme=req.theme,
                )
            else:
                raise HTTPException(400, f"Unknown type: {req.type}. Use: flowchart, architecture, sequence, mindmap, mermaid")

            # Read generated file
            with open(output_path, "r") as f:
                excalidraw_json = json.load(f)

            # Generate SVG
            svg_path = os.path.join(tmpdir, "diagram.svg")
            export_to_svg(output_path, svg_path)
            with open(svg_path, "r") as f:
                svg_content = f.read()

            return {
                "excalidraw": excalidraw_json,
                "svg": svg_content,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
```

> **注意：** `create_flowchart_impl` 等函数名需要在 excalidraw-mcp 引擎中确认实际名称。MCP 工具注册的函数可能需要提取出纯逻辑部分（不依赖 MCP context）。如果引擎没有独立的 `_impl` 函数，Task 1 需要先在引擎里做一层解耦（见 Task 1B）。

**Step 3: 写 Dockerfile**

```dockerfile
# api/Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 4: 本地测试 API**

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "type": "flowchart",
    "data": {
      "nodes": [{"label": "开始"}, {"label": "处理"}, {"label": "结束"}],
      "edges": [{"from": "开始", "to": "处理"}, {"from": "处理", "to": "结束"}]
    },
    "title": "测试流程"
  }'
```

Expected: 返回 JSON，包含 `excalidraw` 和 `svg` 字段。

**Step 5: Commit**

```bash
git add api/
git commit -m "feat: add diagrams API service (FastAPI + excalidraw engine)"
```

---

## Task 1B: 引擎解耦（如需要）

**目标：** 如果 excalidraw-mcp 的工具函数耦合了 MCP context（无法独立调用），需要在引擎中提取纯逻辑层。

**Files:**
- Modify: `excalidraw-mcp/src/excalidraw_mcp/tools/flowchart.py` — 提取 `_impl` 函数

**做法：** 检查每个工具函数，看它是否可以不通过 MCP 直接调用。如果注册方式是 `@mcp.tool()` 装饰器包裹的普通函数，则可以直接 import 调用（跳过此 Task）。如果函数依赖 MCP context，则需要提取。

---

## Task 2: 前端页面

**目标：** 创建 diagrams.html 页面，包含图表类型选择器、文本输入框、生成按钮、SVG 预览区、下载按钮。

**Files:**
- Create: `diagrams.html` — 图表生成页面

**Step 1: 创建页面**

页面结构：
```
┌─────────────────────────────┐
│  diagrams.maaker.ai         │
│  AI 手绘图表生成器            │
├─────────────────────────────┤
│  [流程图] [架构图] [时序图]   │
│  [思维导图] [Mermaid 导入]   │
├─────────────────────────────┤
│  ┌─────────────────────────┐│
│  │  描述你的图表...          ││
│  │  （文本框）              ││
│  └─────────────────────────┘│
│  [✨ 生成图表]               │
├─────────────────────────────┤
│  ┌─────────────────────────┐│
│  │                         ││
│  │    SVG 预览区            ││
│  │                         ││
│  └─────────────────────────┘│
│  [下载 .excalidraw] [下载 SVG]│
├─────────────────────────────┤
│  Powered by Maaker.AI       │
└─────────────────────────────┘
```

技术要求：
- 纯 HTML + Tailwind CDN（和 index.html 一致）
- 配色：白底 + teal (#0D9488) 点缀
- 移动端优先
- 图表类型切换时，输入框 placeholder 变化（提供示例）
- 每种图表类型提供一个 "试试这个" 预填示例按钮
- 生成时显示 loading 动画
- SVG 预览支持缩放（pinch-zoom / scroll-zoom）
- 下载 .excalidraw 文件（JSON blob）和 SVG 文件

**Step 2: 每种图表类型的输入方式**

| 类型 | 输入方式 | 示例 placeholder |
|------|---------|-----------------|
| 流程图 | 结构化表单（节点列表 + 连线） 或 自然语言 | "用户请求 → 负载均衡 → API 服务 → 数据库" |
| 架构图 | 分层描述 | "前端层: React, Next.js / 后端层: API Server, Auth / 数据层: PostgreSQL, Redis" |
| 时序图 | 参与者 + 消息列表 | "用户 → 服务器: 登录请求 / 服务器 → 数据库: 查询用户 / 数据库 → 服务器: 返回结果" |
| 思维导图 | 层级描述 | "AI 技术: 机器学习(监督学习, 无监督学习), 深度学习(CNN, RNN), NLP(GPT, BERT)" |
| Mermaid | 直接粘贴 Mermaid 代码 | "graph LR\n  A[开始] --> B{判断}\n  B -->|是| C[结束]" |

MVP 阶段：**每种类型用结构化表单**，不做自然语言理解（自然语言需要 LLM，增加成本和复杂度）。

**Step 3: JavaScript 逻辑**

核心流程：
1. 用户选择图表类型 → 切换输入表单
2. 用户填写表单 → 点击生成
3. 前端组装 JSON → POST /api/generate
4. 收到响应 → 显示 SVG 预览
5. 下载按钮 → 创建 Blob 下载

```javascript
const API_URL = "https://api.maaker.ai/diagrams"; // 或实际 API 地址

async function generateDiagram() {
  const type = currentType;
  const data = collectFormData(type);
  const title = document.getElementById("title-input").value || null;

  const res = await fetch(`${API_URL}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type, data, title }),
  });

  if (!res.ok) throw new Error(await res.text());
  const result = await res.json();

  // 显示 SVG 预览
  document.getElementById("preview").innerHTML = result.svg;

  // 存储供下载
  window._lastResult = result;
}

function downloadExcalidraw() {
  const blob = new Blob([JSON.stringify(window._lastResult.excalidraw, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "diagram.excalidraw";
  a.click();
}

function downloadSvg() {
  const blob = new Blob([window._lastResult.svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "diagram.svg";
  a.click();
}
```

**Step 4: Commit**

```bash
git add diagrams.html
git commit -m "feat: add diagrams page with type selector, form input, and preview"
```

---

## Task 3: 部署 API 到服务器

**目标：** 在 1.15.12.53 上用 Docker 部署 API 服务，配置 Nginx 反向代理。

**Files:**
- Create: `api/docker-compose.yml`

**Step 1: docker-compose.yml**

```yaml
# api/docker-compose.yml
version: "3.8"
services:
  diagrams-api:
    build: .
    ports:
      - "8100:8000"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

**Step 2: SSH 到服务器部署**

```bash
# 本地：上传 API 代码
scp -r api/ xiaopang@1.15.12.53:/opt/diagrams-api/

# 服务器上：
ssh xiaopang@1.15.12.53
cd /opt/diagrams-api
docker compose up -d --build

# 验证
curl http://localhost:8100/health
```

**Step 3: 配置 Nginx 反向代理**

在服务器上添加 Nginx 配置，让 API 通过 HTTPS 可访问：

```nginx
# /etc/nginx/sites-available/diagrams-api
server {
    listen 80;
    server_name api.maaker.cn;  # 复用已有域名，加 /diagrams 路径

    location /diagrams/ {
        proxy_pass http://127.0.0.1:8100/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

或者用已有的 api.maaker.cn 配置加一个 location block。

**Step 4: 验证端到端**

```bash
curl -X POST https://api.maaker.cn/diagrams/api/generate \
  -H "Content-Type: application/json" \
  -d '{"type":"flowchart","data":{"nodes":[{"label":"A"},{"label":"B"}],"edges":[{"from":"A","to":"B"}]}}'
```

**Step 5: Commit**

```bash
git add api/docker-compose.yml
git commit -m "feat: add docker-compose for diagrams API deployment"
```

---

## Task 4: Cloudflare Pages 路由配置

**目标：** 配置 diagrams.maaker.ai 子域名指向 diagrams.html。

**做法有两种：**

**方案 A（简单）：** 不做子域名，直接用 `maaker.ai/diagrams.html`
- 零配置，Cloudflare Pages 自动 serve 静态文件
- URL 不够品牌化

**方案 B（推荐）：** Cloudflare Pages 支持 `_redirects` 或 `_routes.json`
- 在 Cloudflare DNS 给 `diagrams.maaker.ai` 加 CNAME → `maaker-landing.pages.dev`
- 用 `functions/diagrams.js` 或 `_redirects` 做路由

**MVP 建议：** 先用方案 A（`maaker.ai/diagrams`），快速上线后再加子域名。

**Step 1: 添加 _redirects 文件**

```
# _redirects
/diagrams  /diagrams.html  200
```

**Step 2: Commit & Deploy**

```bash
git add _redirects
git commit -m "feat: add /diagrams route redirect"
npx wrangler pages deploy . --project-name=maaker-landing --commit-dirty=true
```

---

## Task 5: 端到端测试

**目标：** 验证完整流程：用户访问页面 → 选择图表类型 → 输入数据 → 生成 → 预览 → 下载。

**测试用例：**

| # | 图表类型 | 输入 | 预期 |
|---|---------|------|------|
| 1 | 流程图 | 3 个节点 + 2 条边 | SVG 显示 3 个矩形 + 2 条箭头 |
| 2 | 架构图 | 2 层 3 组件 | SVG 显示分层布局 |
| 3 | 时序图 | 2 参与者 3 消息 | SVG 显示生命线和箭头 |
| 4 | 思维导图 | 根 + 3 分支各 2 叶子 | SVG 显示树形展开 |
| 5 | Mermaid | `graph LR; A-->B-->C` | SVG 显示流程图 |
| 6 | 下载 .excalidraw | 生成后点击下载 | 浏览器下载 .excalidraw 文件 |
| 7 | 下载 SVG | 生成后点击下载 | 浏览器下载 .svg 文件 |
| 8 | 中文内容 | 流程图节点用中文 | SVG 中文字正确显示 |
| 9 | 错误处理 | 空输入点击生成 | 显示友好错误提示 |

---

## 任务依赖关系

```
Task 1 (API) ──→ Task 3 (部署)
    ↓                 ↓
Task 1B (解耦，如需)   Task 5 (端到端测试)
    ↑                 ↑
Task 2 (前端) ──→ Task 4 (路由)
```

**并行可能：** Task 1 和 Task 2 可以同时做（API 和前端独立开发）。

---

## 风险和注意事项

1. **引擎函数解耦**：excalidraw-mcp 的工具函数是通过 `@mcp.tool()` 注册的，需要确认能否脱离 MCP context 直接 import 调用。如果不行，需要 Task 1B 做解耦。
2. **SVG 导出**：引擎的 `export_to_svg` 函数需要确认是否依赖外部工具（如 headless browser）。如果依赖，Docker 镜像需要安装对应依赖。
3. **CORS**：API 部署在 api.maaker.cn，前端在 maaker.ai，需要正确配置跨域。
4. **国内网络**：API 在国内服务器，海外用户访问可能慢。MVP 先不管，后续可迁移到美国服务器。
