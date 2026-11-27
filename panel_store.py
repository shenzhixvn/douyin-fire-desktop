"""
桌面控制面板的数据读写层。

只负责 config.json / result.json / history.json / run.log 的读取与回写，
不依赖 tkinter，便于单独测试。所有文件缺失或损坏都按空数据处理，不抛异常。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


# 抖音 Web 表情面板里已知的原生表情（顺序即面板位置，可作为 fallback_index）
KNOWN_STICKERS: list[str] = [
    "续火花", "比心", "在干嘛", "笑死", "麻了", "躺平", "摇骰子", "猜拳",
    "开心", "嗨", "吹泡泡", "黑人问号", "早上好", "晚上好", "早点睡",
    "爱心", "便便", "戳一戳", "绝了", "已阅", "生日祝福",
]


@dataclass
class Entry:
    """一条发送对象（一个好友 / 一个群聊）。"""

    name: str
    sticker: str = ""
    msg_type: str = "sticker"  # sticker / text / image
    raw_message: dict[str, Any] = field(default_factory=dict)


@dataclass
class PanelData:
    entries: list[Entry] = field(default_factory=list)
    interval_min: int = 60
    interval_max: int = 60
    prevent_duplicates: bool = True
    continue_on_error: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _extract_message(message: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """从 message dict 取出 (msg_type, 展示名, 原始 message)。"""
    if not isinstance(message, dict):
        return "text", "", {}
    mtype = message.get("type", "text")
    if mtype == "sticker" or mtype == "douyin_sticker":
        name = message.get("sticker", message.get("value", ""))
        return "sticker", str(name or ""), dict(message)
    if mtype == "image":
        name = message.get("path", message.get("value", ""))
        return "image", str(name or ""), dict(message)
    content = message.get("content", message.get("value", ""))
    return "text", str(content or ""), dict(message)


def load_config(path: Path) -> PanelData:
    raw = _read_json(path)
    data = PanelData()
    if not isinstance(raw, dict):
        return data

    data.raw = raw
    interval = raw.get("send_interval_seconds", {})
    if isinstance(interval, dict):
        data.interval_min = int(interval.get("min", 60))
        data.interval_max = int(interval.get("max", 60))
    data.prevent_duplicates = bool(raw.get("prevent_duplicates", True))
    data.continue_on_error = bool(raw.get("continue_on_error", True))

    targets_raw = raw.get("targets")
    if not isinstance(targets_raw, list) and "friends" in raw:
        friends = raw.get("friends")
        messages = raw.get("messages")
        if isinstance(friends, list) and isinstance(messages, list):
            targets_raw = [{"name": n, "messages": messages} for n in friends]

    if isinstance(targets_raw, list):
        for item in targets_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            messages = item.get("messages")
            if isinstance(messages, list) and messages:
                for msg in messages:
                    mtype, label, raw_msg = _extract_message(msg)
                    data.entries.append(Entry(name=name, sticker=label,
                                             msg_type=mtype, raw_message=raw_msg))
            else:
                data.entries.append(Entry(name=name))
    return data


def _sticker_entry(name: str) -> dict[str, Any]:
    index = KNOWN_STICKERS.index(name) if name in KNOWN_STICKERS else None
    entry: dict[str, Any] = {"label": name}
    if index is not None:
        entry["fallback_index"] = index
    return entry


def save_config(path: Path, data: PanelData) -> None:
    """回写为 targets 结构，保留 raw 里未被面板管理的字段。"""
    targets: list[dict[str, Any]] = []
    stickers: dict[str, Any] = {}

    for e in data.entries:
        name = e.name.strip()
        if not name:
            continue
        if e.msg_type == "sticker":
            msg: dict[str, Any] = {"type": "sticker", "value": e.sticker}
            if e.sticker:
                stickers.setdefault(e.sticker, _sticker_entry(e.sticker))
        elif e.msg_type == "image":
            msg = {"type": "image", "path": e.sticker}
        else:
            msg = {"type": "text", "value": e.sticker}
        targets.append({"name": name, "messages": [msg]})

    out: dict[str, Any] = {
        "task_id": data.raw.get("task_id", "daily-streak"),
        "timezone": data.raw.get("timezone", "Asia/Shanghai"),
        "targets": targets,
        "stickers": stickers,
        "send_interval_seconds": {"min": data.interval_min, "max": data.interval_max},
        "continue_on_error": data.continue_on_error,
        "prevent_duplicates": data.prevent_duplicates,
    }
    # 回填其余保留字段
    for key in ("target_open_retries", "target_open_timeout_seconds",
                "dingtalk_webhook", "dingtalk_secret"):
        if key in data.raw:
            out[key] = data.raw[key]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_result(path: Path) -> list[dict[str, Any]]:
    """读取最近一次 result.json，按顺序返回 [{status, sent, error}]。"""
    raw = _read_json(path)
    if not isinstance(raw, dict):
        return []
    results = raw.get("results")
    if not isinstance(results, list):
        return []
    out: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        out.append({
            "status": str(item.get("status", "unknown")),
            "sent": int(item.get("sent", 0) or 0),
            "error": item.get("error"),
            "target": item.get("target"),
        })
    return out


def _today_key_prefix(task_id: str, tz_name: str) -> str:
    try:
        today = datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except ZoneInfoNotFoundError:
        today = datetime.now().date().isoformat()
    return f"{task_id}:{today}:"


def load_today_sent(history_path: Path, task_id: str, tz_name: str) -> set[str]:
    """返回当天已经成功发送过的对象昵称集合。"""
    raw = _read_json(history_path)
    if not isinstance(raw, dict):
        return set()
    prefix = _today_key_prefix(task_id, tz_name)
    sent: set[str] = set()
    for key, val in raw.items():
        if not isinstance(key, str) or not key.startswith(prefix):
            continue
        status = val.get("status") if isinstance(val, dict) else None
        if status == "success":
            # key = task_id:date:target:message_id
            parts = key.split(":")
            if len(parts) >= 3:
                sent.add(parts[2])
    return sent


def load_result_summary(path: Path) -> dict[str, Any]:
    """最近一次运行的汇总信息。"""
    raw = _read_json(path)
    if not isinstance(raw, dict):
        return {"finished_at": "", "dry_run": None, "total": 0, "success": 0, "failed": 0}
    results = raw.get("results")
    if not isinstance(results, list):
        results = []
    statuses = [str(r.get("status", "unknown")) for r in results if isinstance(r, dict)]
    return {
        "finished_at": str(raw.get("finished_at", "") or ""),
        "dry_run": raw.get("dry_run"),
        "total": len(statuses),
        "success": sum(s == "success" for s in statuses),
        "failed": sum(s == "failed" for s in statuses),
    }


def read_log_tail(path: Path, lines: int = 200) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    tail = content.splitlines()[-lines:]
    return "\n".join(tail)
