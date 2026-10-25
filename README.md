# PDF 智能解析

上传 PDF → 自动识别文档类型 → 按类型提取重点内容 → 输出给人看的报告。

当前已实现第一类「工程图纸 → 图纸识别报告」，并打通前后端。接口契约见 [docs/design.md](docs/design.md) 第 9 章。

## 项目结构

```text
.
├── index.html            # 前端（单文件，零依赖）
├── backend/
│   ├── server.py         # FastAPI 服务（HTTP 接口）
│   ├── parse_pdf.py      # 解析核心（CLI + 可复用函数）
│   └── requirements.txt
├── prompts/              # 提示词（核心资产）
├── docs/design.md        # 设计文档与接口契约
└── output/               # 生成的报告（已 gitignore）
```

## 快速开始

1. 配置 API key：编辑根目录 `.env`，填入 `DEEPSEEK_API_KEY`。

2. 启动后端：

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
```

3. 打开前端：用浏览器打开 `index.html` 即可（前端默认请求 `http://localhost:8000`）。

4. 验证后端：`curl http://127.0.0.1:8000/health` 返回 `{"status":"ok"}`。

## 命令行解析（不启服务）

```bash
python3 backend/parse_pdf.py 某张图纸.pdf
```

数字 PDF 自动走文本层解析；扫描件自动走视觉切片解析。

## 说明

- 前端默认关闭演示模式（`DEMO_MODE: false`），直接调后端；如需离线预览，把 `index.html` 顶部 `CONFIG.DEMO_MODE` 改为 `true`。
- 后端已开启 CORS（`*`），`file://` 打开的前端可直接调用。
- `.env`、`tmp/`、`output/` 已加入 `.gitignore`，不会进 git。
