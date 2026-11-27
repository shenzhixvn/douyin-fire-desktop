"""
抖音自动续火花 - 桌面管理面板

功能：
- 好友 / 群聊的添加、删除、表情修改，保存到 config.json
- 查看最近一次运行结果（成功 / 失败 / 发送数 / 错误）与当日已发记录
- 扫码登录、Dry Run、正式运行、停止、打开日志目录
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

import panel_store as ps


def get_app_dir() -> Path:
    """应用根目录：兼容源码运行与 PyInstaller 打包后的 exe。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent.resolve()
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
os.chdir(APP_DIR)
(APP_DIR / "artifacts").mkdir(exist_ok=True)

CONFIG_PATH = APP_DIR / "config.json"
RESULT_PATH = APP_DIR / "artifacts" / "result.json"
HISTORY_PATH = APP_DIR / "artifacts" / "history.json"
LOG_PATH = APP_DIR / "artifacts" / "run.log"

# 打包后绿色软件模式：优先使用 exe 同目录下的浏览器
_bundled = APP_DIR / "ms-playwright"
if _bundled.is_dir():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(_bundled)

STATUS_COLORS = {
    "success": "#2e9e5b",
    "failed": "#d9534f",
    "skipped": "#8a8a8a",
    "duplicate": "#8a8a8a",
    "unknown": "#8a8a8a",
}

TYPE_LABEL = {"sticker": "表情", "text": "文字", "image": "图片"}


class DouyinPanel:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("抖音自动续火花 · 管理面板")
        self.root.geometry("980x660")
        self.root.minsize(880, 560)

        self.data = ps.PanelData()
        self._process: subprocess.Popen | None = None
        self._log_thread: threading.Thread | None = None

        self._build_ui()
        self.refresh()

    # ── 界面构建 ──────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        # 顶部标题 + 状态
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill=tk.X)
        ttk.Label(top, text="🔥 抖音自动续火花", font=("Microsoft YaHei UI", 16, "bold")).pack(side=tk.LEFT)
        self.status_label = ttk.Label(top, text="", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)

        # ── 好友管理区 ──
        manage = ttk.LabelFrame(self.root, text="好友与表情管理", padding=8)
        manage.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 6))

        columns = ("name", "sticker", "mtype", "status", "sent", "today", "error")
        self.tree = ttk.Treeview(manage, columns=columns, show="headings", selectmode="extended")
        headings = {
            "name": ("昵称 / 群聊", 170),
            "sticker": ("表情 / 内容", 130),
            "mtype": ("类型", 70),
            "status": ("最近状态", 90),
            "sent": ("发送数", 70),
            "today": ("今日已发", 80),
            "error": ("错误信息", 220),
        }
        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=tk.CENTER if col != "error" else tk.W)
        self.tree.tag_configure("success", foreground=STATUS_COLORS["success"])
        self.tree.tag_configure("failed", foreground=STATUS_COLORS["failed"])
        self.tree.tag_configure("gray", foreground=STATUS_COLORS["unknown"])

        vsb = ttk.Scrollbar(manage, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 管理按钮行
        btn_row = ttk.Frame(manage, padding=(0, 6, 0, 0))
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="➕ 添加好友", command=self.add_entry).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="✏️ 修改表情", command=self.edit_entry).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="🗑 删除选中", command=self.remove_entries).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="💾 保存配置", command=self.save_entries).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="🔄 刷新", command=self.refresh).pack(side=tk.LEFT, padx=3)

        # 间隔设置
        interval_row = ttk.Frame(manage, padding=(0, 6, 0, 0))
        interval_row.pack(fill=tk.X)
        ttk.Label(interval_row, text="好友间隔（秒）：").pack(side=tk.LEFT)
        self.interval_min = tk.StringVar(value="60")
        self.interval_max = tk.StringVar(value="60")
        ttk.Entry(interval_row, textvariable=self.interval_min, width=6).pack(side=tk.LEFT)
        ttk.Label(interval_row, text=" ~ ").pack(side=tk.LEFT)
        ttk.Entry(interval_row, textvariable=self.interval_max, width=6).pack(side=tk.LEFT)

        # ── 任务情况区 ──
        report = ttk.LabelFrame(self.root, text="任务情况", padding=8)
        report.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        self.summary_label = ttk.Label(report, text="", foreground="#333")
        self.summary_label.pack(anchor=tk.W, pady=(0, 4))

        log_frame = ttk.Frame(report)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Listbox(
            log_frame, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            height=10, relief=tk.SUNKEN, activestyle=tk.NONE,
        )
        log_vsb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_vsb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── 底部操作 ──
        action = ttk.Frame(self.root, padding=(12, 6, 12, 10))
        action.pack(fill=tk.X)
        ttk.Button(action, text="📱 扫码登录", command=self.do_login).pack(side=tk.LEFT, padx=3)
        ttk.Button(action, text="🧪 Dry Run", command=self.do_dry_run).pack(side=tk.LEFT, padx=3)
        ttk.Button(action, text="🚀 正式运行", command=self.do_run).pack(side=tk.LEFT, padx=3)
        ttk.Button(action, text="🛑 停止", command=self.stop_process).pack(side=tk.LEFT, padx=3)
        ttk.Button(action, text="📂 日志目录", command=self.open_logs).pack(side=tk.RIGHT, padx=3)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=12, pady=(0, 6))

    # ── 数据刷新 ──────────────────────────────────────────────────────
    def refresh(self) -> None:
        self.data = ps.load_config(CONFIG_PATH)
        self.interval_min.set(str(self.data.interval_min))
        self.interval_max.set(str(self.data.interval_max))

        results = ps.load_last_result(RESULT_PATH)
        summary = ps.load_result_summary(RESULT_PATH)
        today_sent = ps.load_today_sent(HISTORY_PATH, self.data.raw.get("task_id", "daily-streak"),
                                        self.data.raw.get("timezone", "Asia/Shanghai"))

        self.tree.delete(*self.tree.get_children())
        for i, entry in enumerate(self.data.entries):
            res = results[i] if i < len(results) else {}
            status = res.get("status", "—")
            sent = res.get("sent", 0)
            error = res.get("error") or ""
            tag = status if status in STATUS_COLORS else "gray"
            today = "✅ 已发" if entry.name in today_sent else ""
            self.tree.insert(
                "", tk.END,
                values=(entry.name, entry.sticker, TYPE_LABEL.get(entry.msg_type, entry.msg_type),
                        status, sent, today, error),
                tags=(tag,),
            )

        finished = summary["finished_at"] or "暂无记录"
        self.summary_label.config(
            text=f"最近运行：{finished}　|　总数 {summary['total']}　成功 {summary['success']}　"
                 f"失败 {summary['failed']}"
        )

        login_ok = (APP_DIR / "storage-state.json").exists()
        self.status_label.config(
            text=("✅ 已登录" if login_ok else "⚠️ 未登录") + f"　|　配置 {len(self.data.entries)} 人"
        )
        self._show_log_tail()

    def _show_log_tail(self) -> None:
        self._set_log(ps.read_log_tail(LOG_PATH, 200))

    # ── 表格操作 ───────────────────────────────────────────────────────
    def _selected_indexes(self) -> list[int]:
        ids = self.tree.selection()
        return [self.tree.index(i) for i in ids]

    def add_entry(self) -> None:
        name, sticker, ok = self._ask_entry("添加好友", "", ps.KNOWN_STICKERS)
        if not ok:
            return
        if not name.strip():
            messagebox.showwarning("提示", "昵称不能为空")
            return
        if any(e.name == name.strip() for e in self.data.entries):
            messagebox.showwarning("提示", "该昵称已存在")
            return
        self.data.entries.append(ps.Entry(name=name.strip(), sticker=sticker.strip(), msg_type="sticker"))
        self.refresh()

    def edit_entry(self) -> None:
        indexes = self._selected_indexes()
        if len(indexes) != 1:
            messagebox.showinfo("提示", "请先选中要修改的一条")
            return
        idx = indexes[0]
        entry = self.data.entries[idx]
        name, sticker, ok = self._ask_entry("修改表情", entry.sticker, ps.KNOWN_STICKERS, entry.name)
        if not ok:
            return
        if not name.strip():
            messagebox.showwarning("提示", "昵称不能为空")
            return
        entry.name = name.strip()
        entry.sticker = sticker.strip()
        entry.msg_type = "sticker"
        self.refresh()

    def remove_entries(self) -> None:
        indexes = sorted(self._selected_indexes(), reverse=True)
        if not indexes:
            messagebox.showinfo("提示", "请先选中要删除的条目")
            return
        if not messagebox.askyesno("确认", f"确定删除选中的 {len(indexes)} 条吗？"):
            return
        for idx in indexes:
            del self.data.entries[idx]
        self.refresh()

    def save_entries(self) -> None:
        if not self.data.entries:
            messagebox.showwarning("提示", "至少需要保留一个发送对象")
            return
        try:
            self.data.interval_min = int(self.interval_min.get())
            self.data.interval_max = int(self.interval_max.get())
        except ValueError:
            messagebox.showwarning("提示", "间隔必须是数字")
            return
        if self.data.interval_min < 0 or self.data.interval_max < self.data.interval_min:
            messagebox.showwarning("提示", "间隔需满足 0 ≤ min ≤ max")
            return
        for e in self.data.entries:
            if not e.name.strip():
                messagebox.showwarning("提示", "存在空昵称，请先完善")
                return
            if e.msg_type == "sticker" and not e.sticker.strip():
                messagebox.showwarning("提示", f"「{e.name}」未填写表情")
                return
        ps.save_config(CONFIG_PATH, self.data)
        messagebox.showinfo("完成", "配置已保存")
        self.refresh()

    def _ask_entry(self, title: str, sticker: str, values: list[str], name: str = "") -> tuple[str, str, bool]:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        result = {"name": name, "sticker": sticker, "ok": False}

        ttk.Label(dialog, text="昵称 / 群聊：").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_var = tk.StringVar(value=name)
        ttk.Entry(dialog, textvariable=name_var, width=24).grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="表情：").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        sticker_var = tk.StringVar(value=sticker)
        combo = ttk.Combobox(dialog, textvariable=sticker_var, values=values, width=22)
        combo.grid(row=1, column=1, padx=10, pady=10)

        def confirm():
            result["name"] = name_var.get()
            result["sticker"] = sticker_var.get()
            result["ok"] = True
            dialog.destroy()

        ttk.Button(dialog, text="确定", command=confirm).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(dialog, text="取消", command=dialog.destroy).grid(row=2, column=1, padx=10, pady=10)
        dialog.bind("<Return>", lambda _: confirm())
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result["name"], result["sticker"], result["ok"]

    # ── 子进程运行 ───────────────────────────────────────────────────
    def _set_log(self, text: str) -> None:
        self.log_text.delete(0, tk.END)
        for line in text.splitlines():
            self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)

    def _append_log(self, text: str) -> None:
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _run_script(self, script_args: list[str], label: str) -> None:
        if self._process and self._process.poll() is None:
            messagebox.showwarning("提示", "已有任务正在运行，请先停止")
            return
        self._set_log(f"── 开始: {label} ──")
        self.progress.start(10)

        cmd = [sys.executable] + script_args
        self._append_log("执行: " + " ".join(cmd))
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self._process = subprocess.Popen(
                cmd, cwd=str(APP_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", creationflags=creationflags,
            )
        except Exception as exc:
            self._append_log(f"启动失败: {exc}")
            self.progress.stop()
            return

        def reader():
            assert self._process and self._process.stdout
            for line in self._process.stdout:
                self.root.after(0, self._append_log, line.rstrip())
            self._process.wait()
            code = self._process.returncode
            self.root.after(0, self._on_done, label, code)

        self._log_thread = threading.Thread(target=reader, daemon=True)
        self._log_thread.start()

    def _on_done(self, label: str, return_code: int) -> None:
        self.progress.stop()
        status = "✅ 成功" if return_code == 0 else f"❌ 退出码 {return_code}"
        self._append_log(f"── 结束: {label} {status} ──")
        self._process = None
        self.refresh()

    def stop_process(self) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            self._append_log("── 已手动停止 ──")
            self.progress.stop()
        else:
            messagebox.showinfo("提示", "当前没有运行中的任务")

    def do_login(self) -> None:
        self._run_script(["scripts/login_auto.py"], "扫码登录")

    def do_dry_run(self) -> None:
        self._run_script(["run.py", "--dry-run"], "Dry Run 测试")

    def do_run(self) -> None:
        if not messagebox.askyesno("确认", "确认要正式发送表情吗？\n建议先运行 Dry Run 测试。"):
            return
        self._run_script(["run.py"], "正式运行")

    def open_logs(self) -> None:
        log_dir = APP_DIR / "artifacts"
        log_dir.mkdir(exist_ok=True)
        if os.name == "nt":
            os.startfile(str(log_dir))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(log_dir)])


def main() -> None:
    root = tk.Tk()
    DouyinPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
