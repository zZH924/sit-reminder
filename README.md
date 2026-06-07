# 💺 久坐放松提醒

基于 FastAPI + 原生 Web 技术构建的久坐放松提醒工具。设置工作时长，定时弹出随机拉伸/放松动作，配合提示音和系统通知，帮你养成健康的工作习惯。

## 功能列表

| 功能 | 说明 |
|------|------|
| ⏱️ 自定义计时 | 1-120 分钟工作时长，实时倒计时 + 进度条 |
| 🎯 随机放松动作 | 内置 12 种拉伸/眼保健操/深呼吸，每次随机抽取 |
| 🔊 提示音提醒 | Web Audio API 合成提示音，后台标签页也能听到 |
| 🔔 系统通知 | 浏览器原生通知，切到其他应用也能弹出 |
| 💾 数据持久化 | localStorage 存储，刷新不丢失，跨天自动重置 |
| 🌙 深色模式 | 一键切换，跟随系统偏好，刷新保持 |
| ⏸️ 暂停/继续 | 计时中随时暂停，接电话不慌 |
| 🍅 番茄钟 | 25+5 预设，4 轮后自动长休 15 分钟，轮次追踪 |
| ⏰ 定时跳过 | 休息时"再工作 5 分钟"，最多 3 次 |
| 📈 统计图表 | 近 7 天/30 天柱状图，Canvas 原生绘制 |
| 🔥 连续打卡 | 自动计算连续使用天数 |

## 环境要求

- Python 3.10+
- 现代浏览器（Chrome / Edge / Firefox）
- 无需数据库、无需额外服务

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
python server.py
```

浏览器打开 `http://localhost:8000`。

首次使用：点击侧边栏 「🔔 开启浏览器通知」 授权系统通知（可选，不影响其他功能）。

**Windows 用户**：双击 `start.bat` 启动，双击 `stop.bat` 停止。

## 项目结构

```
sit-reminder/
├── server.py               # FastAPI 应用（托管页面 + API）
├── start.bat               # Windows 启动脚本
├── stop.bat                # Windows 停止脚本
├── requirements.txt         # Python 依赖
├── .gitignore
├── static/
│   └── index.html           # 全部前端（HTML + CSS + JS，单文件 ~400 行）
├── data/
│   └── exercises.json       # 放松动作库（12 条，可自行扩展）
├── tests/
│   ├── test_core.py         # 单元测试：状态机 + 数据模型 + API（16 个，0.2s）
│   ├── test_browser.py      # E2E 测试：snooze 完整流程
│   ├── test_pomodoro.py     # E2E 测试：番茄钟 4 轮流程
│   └── screenshots/         # 测试自动截图
└── README.md
```

## 技术架构

```
浏览器                          FastAPI (server.py)
  │                                  │
  ├─ GET / ──────────────────────────┤ 返回 index.html
  ├─ GET /api/exercises ─────────────┤ 返回 12 条动作 JSON
  │                                  │
  │  前端独立完成：                   │
  │  - setInterval 计时器             │
  │  - AudioContext 合成提示音        │
  │  - Notification API 系统通知      │
  │  - localStorage 统计 + 图表       │
  │  - Canvas 原生柱状图              │
```

| 功能 | 实现方式 |
|------|---------|
| 后端 | FastAPI，两个路由：页面托管 + JSON API |
| 前端 | 原生 HTML/CSS/JS，零框架，零 CDN 依赖 |
| 计时器 | `setInterval` + `Date.now()` 差值计算 |
| 提示音 | `AudioContext` + `OscillatorNode`，后台标签页可用 |
| 系统通知 | `Notification.requestPermission()` + `new Notification()` |
| 图表 | 原生 Canvas API 手绘柱状图（圆角、网格线、标签） |
| 深色模式 | CSS 变量 + `data-theme` 属性 + `prefers-color-scheme` 自动检测 |
| 数据存储 | `localStorage`，单 key 存储全部状态 |

## 常见问题

**Q: 提示音在后台标签页能听到吗？**
A: 能。Web Audio API 不受浏览器自动播放策略限制。

**Q: 系统通知不弹？**
A: 点侧边栏「🔔 开启浏览器通知」授权。如显示"被拒绝"，在浏览器设置中手动允许 `localhost:8000`。

**Q: 计时中刷新页面会怎样？**
A: 计时状态丢失，回到就绪。统计数据保留在 localStorage 中不会丢。

**Q: 如何添加自定义放松动作？**
A: 编辑 `data/exercises.json`，按格式新增条目，重启服务。

**Q: 如何运行测试？**
A:
```bash
# 单元测试
python -m pytest tests/test_core.py -v

# 浏览器 E2E 测试（需要服务在 :8000 运行）
python tests/test_browser.py
python tests/test_pomodoro.py
```
