# 🔥 抖音自动续火花（桌面面板版）

> 基于 Python + Playwright 的抖音私信自动发送工具，附带一个图形化桌面管理面板。
> 通过模拟真实浏览器操作，按配置自动向指定好友 / 群聊发送抖音原生表情、文字或图片，支持 Dry Run 校验、防重复发送、运行结果查看与日志诊断。

## ✨ 功能

### 桌面管理面板（`gui.py` + `panel_store.py`）

- **好友 / 表情管理**：表格形式添加、修改、删除发送对象，为每个人单独选择表情
- **任务情况查看**：最近一次运行的总数 / 成功 / 失败，每人状态、发送数、当日是否已发、错误信息
- **运行控制**：扫码登录、Dry Run 测试、正式运行、手动停止、打开日志目录
- **间隔设置**：自定义相邻对象之间的等待秒数（默认 60 秒）
- **日志面板**：实时滚动展示运行日志尾部

### 后端能力（`app/`）

- 原生表情 / 文字 / 图片多种消息类型，支持候选消息随机选择
- 多好友、多账号串行执行
- 防重复发送：记录发送历史，当日已成功的对象不重复发
- 失败继续、失败重试、日志 / 截图 / Trace 诊断
- 钉钉机器人、通用 Webhook（企业微信、飞书、Slack、Discord、Telegram 等）通知
- 支持 GitHub Actions、Docker、Linux systemd、Windows 任务计划等定时方式

## 🚀 快速开始（Windows）

### 1. 环境准备

- Python 3.11+（安装时勾选 **Add Python to PATH**）
- 首次运行会自动安装依赖与 Chromium 浏览器（约 150MB，需联网）

### 2. 源码运行

双击 `启动.bat`：

1. 首次运行自动安装依赖、下载 Chromium
2. 面板窗口打开后，点 **📱 扫码登录**，在弹出的浏览器中完成扫码
3. 在表格里 **➕ 添加好友**、选择表情，点 **💾 保存配置**
4. 先点 **🧪 Dry Run** 校验登录与会话定位，确认无误后再点 **🚀 正式运行**

### 3. 打包成可执行程序

双击 `build.bat`，脚本自动创建虚拟环境、安装依赖、打包并复制 Chromium。
产物位于：

```text
dist\抖音自动续火花-桌面\抖音自动续火花-桌面.exe
```

> 由于 Playwright 自带浏览器驱动（Node 运行时）体积较大，打包产物为「exe + 依赖文件夹」的目录形态；整个文件夹拷贝到其他 Windows 电脑即可运行，目标机需安装 VC++ 运行库。

## 🖥️ 面板按钮说明

| 按钮 | 功能 |
| --- | --- |
| ➕ 添加好友 | 新增一个发送对象，填写昵称并选择表情 |
| ✏️ 修改表情 | 选中一条后修改昵称或表情 |
| 🗑 删除选中 | 删除选中的一条或多条（二次确认） |
| 💾 保存配置 | 把表格内容与间隔秒数写入 `config.json` |
| 🔄 刷新 | 重新读取配置、最近结果与日志 |
| 📱 扫码登录 | 打开浏览器扫码，登录态保存到 `storage-state.json` |
| 🧪 Dry Run | 校验登录与配置、定位会话，不实际发送 |
| 🚀 正式运行 | 按配置自动发送消息（发送前需确认） |
| 🛑 停止 | 终止当前运行中的任务 |
| 📂 日志目录 | 打开 `artifacts` 目录查看日志、截图与诊断文件 |

## 😀 原生表情清单

面板下拉可选以下抖音原生表情（顺序即表情面板位置）：

续火花、比心、在干嘛、笑死、麻了、躺平、摇骰子、猜拳、开心、嗨、吹泡泡、黑人问号、早上好、晚上好、早点睡、爱心、便便、戳一戳、绝了、已阅、生日祝福。

> 专属表情：在表格里给对应对象单独选表情即可。例如默认所有人发「续火花」，某人单独发「比心」。

## 📄 配置文件 `config.json`

面板保存后使用 `targets` 结构：

```json
{
  "task_id": "daily-streak",
  "timezone": "Asia/Shanghai",
  "targets": [
    {"name": "小杰子", "messages": [{"type": "sticker", "value": "续火花"}]},
    {"name": "孙静蕾", "messages": [{"type": "sticker", "value": "比心"}]}
  ],
  "stickers": {
    "续火花": {"label": "续火花", "fallback_index": 0},
    "比心": {"label": "比心", "fallback_index": 1}
  },
  "send_interval_seconds": {"min": 60, "max": 60},
  "continue_on_error": true,
  "prevent_duplicates": true
}
```

消息类型：

| type | value 说明 |
| --- | --- |
| sticker | 抖音原生表情名称（推荐用于续火花） |
| text | 文字内容 |
| image | 图片路径（PNG / JPG / GIF / WebP） |

## ⏰ 定时自动运行（Windows 任务计划程序）

1. `Win + R` 输入 `taskschd.msc` 回车
2. 创建基本任务，名称 `DouyinAutoFire`
3. 触发器：每天，时间 **00:01**
4. 操作：启动程序
   - 程序 / 脚本：`.venv\Scripts\python.exe`（源码运行）或打包后的 `抖音自动续火花-桌面.exe`
   - 起始于：项目根目录（必须填写，否则找不到配置）
5. 勾选「错过计划后尽快运行」，开机后自动补跑

> 定时任务运行时电脑需开机且联网；登录态失效需重新扫码。

## 🐳 其他部署方式

- [GitHub Actions 部署](docs/github-actions.md)
- [Docker 部署](docs/docker.md)
- [Linux 云服务器部署](docs/server.md)
- [Windows 详细教程](docs/windows.md)

## 🧰 技术栈

| 类别 | 内容 |
| --- | --- |
| 语言 | Python 3.11+ |
| 浏览器自动化 | Playwright + Chromium |
| 桌面界面 | Tkinter / ttk |
| 定时调度 | GitHub Actions / Docker Cron / systemd Timer / Windows 任务计划程序 |
| 环境变量 | python-dotenv |
| 时区 | tzdata |
| 通知 | 钉钉机器人 / 通用 Webhook |

主要依赖：

```text
playwright>=1.54,<2
python-dotenv>=1.1,<2
tzdata>=2025.2
```

## ⚠️ 注意事项

- 昵称必须与抖音列表完全一致（含 emoji、空格）；同名不同账号请用后缀区分（如「葛舒怡」「葛舒怡2」）。
- `storage-state.json`、Cookie、`.env`、钉钉密钥属于登录凭证，**不要提交到公开仓库，也不要分享给他人**。
- 修改配置后建议先运行一次 Dry Run。
- 同一个抖音账号不要同时在多台机器或多个任务里重复运行，避免重复发送。
- 日志、截图、Trace 可能包含聊天信息，请勿直接公开。
- 网络环境或风控可能触发抖音安全验证；Cookie / 登录态失效时需本人重新完成登录。
- 抖音网页结构调整后，自动化选择器可能需要同步适配。

## License

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)。
允许个人学习、研究、修改和非商业用途使用；未经授权不得用于商业用途、收费服务或营利性场景。
