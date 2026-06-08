from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

from .app_config import AppConfig, get_config


class Railway12306Client:
    """Small adapter around the optional 12306 MCP HTTP server."""

    def __init__(self, config: AppConfig | None = None):
        self.config = config or get_config()

    @property
    def enabled(self) -> bool:
        return self.config.has_12306_mcp

    def query_train_option(self, origin: str, destination: str, travel_date: date | str) -> dict[str, Any] | None:
        if not self.enabled or not origin or not destination:
            return None

        arguments = {
            "date": _format_date(travel_date),
            "fromStation": origin,
            "toStation": destination,
            "trainFilterFlags": "GD",
            "earliestStartTime": 6,
            "latestStartTime": 23,
            "sortFlag": "startTime",
            "sortReverse": False,
            "limitedNum": 20,
            "format": "json",
        }
        try:
            result = self._call_tool("get-tickets", arguments)
        except Exception:
            return {
                "ticket_query_source": "12306_mcp",
                "ticket_query_transport": "unavailable",
                "ticket_query_error": "12306-MCP连接或查询失败，暂未拿到当天车票列表。",
                "notice": "12306-MCP暂未返回车票信息，费用按兜底估算；真实班次、余票和票价以12306官方为准。",
            }
        transport = str((result or {}).get("_transport") or "")
        text = _extract_text_content(result)
        tickets = _load_ticket_json(text)
        train_tickets = _ticket_candidates(tickets)
        selected = _select_ticket(tickets)
        if selected is None:
            if train_tickets:
                return {
                    "train_tickets": train_tickets,
                    "selected_train_index": None,
                    "ticket_query_source": "12306_mcp",
                    "ticket_query_transport": transport,
                    "notice": "已通过12306-MCP查到当天车次，但未找到可售座席；费用暂按兜底估算，余票以12306官方为准。",
                }
            interline = self._query_interline_candidates(origin, destination, travel_date, transport)
            if interline:
                return interline
            return {
                "ticket_query_source": "12306_mcp",
                "ticket_query_transport": transport,
                "ticket_query_error": _ticket_query_error(text),
                "notice": "12306-MCP暂未返回车票信息，费用按兜底估算；真实班次、余票和票价以12306官方为准。",
            }

        ticket, seat = selected
        price = _coerce_price(seat.get("price"))
        if price is None:
            return None
        duration_min = _parse_duration_min(ticket.get("lishi"))
        selected_train_index = _selected_train_index(train_tickets, ticket, seat)

        return {
            "one_way_cost": int(round(price)),
            "duration_min": duration_min,
            "train_code": str(ticket.get("start_train_code") or ""),
            "seat_type": str(seat.get("seat_name") or ""),
            "ticket_status": str(seat.get("num") or ""),
            "depart_time": str(ticket.get("start_time") or ""),
            "arrive_time": str(ticket.get("arrive_time") or ""),
            "from_station": str(ticket.get("from_station") or origin),
            "to_station": str(ticket.get("to_station") or destination),
            "query_date": _format_date(travel_date),
            "source": "12306_mcp",
            "ticket_query_source": "12306_mcp",
            "ticket_query_transport": transport,
            "train_tickets": train_tickets,
            "selected_train_index": selected_train_index,
            "notice": "已通过12306-MCP查询到参考车次；票价和余票会变化，购票、改签和最终价格以12306官方为准。",
        }

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        errors: list[str] = []
        try:
            return self._call_http_tool(name, arguments)
        except Exception as exc:
            errors.append(f"HTTP: {exc}")
            print(f"[12306-mcp] HTTP调用失败，尝试stdio兜底：{exc}", flush=True)

        try:
            return self._call_stdio_tool(name, arguments)
        except Exception as exc:
            errors.append(f"stdio: {exc}")
            print(f"[12306-mcp] stdio调用失败：{exc}", flush=True)

        if errors:
            raise RuntimeError("；".join(errors))
        return None

    def _call_http_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        url = _mcp_endpoint(self.config.railway_mcp_url)
        if not url:
            raise RuntimeError("未配置RAILWAY_MCP_URL")
        payload = {
            "jsonrpc": "2.0",
            "id": f"{name}-1",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        response = requests.post(
            url,
            headers={"Accept": "application/json, text/event-stream"},
            json=payload,
            timeout=self.config.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            return None
        result = data.get("result")
        if isinstance(result, dict):
            result["_transport"] = "http"
            print(
                f"[12306-mcp] HTTP调用成功：{name} {arguments.get('fromStation')}->{arguments.get('toStation')} {arguments.get('date')}",
                flush=True,
            )
        return result

    def _call_stdio_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        script = _find_12306_mcp_script()
        node = shutil.which("node")
        if not script or not node:
            raise RuntimeError("未找到node或12306-mcp脚本")

        timeout_seconds = max(30, int(self.config.request_timeout or 0))
        process = subprocess.Popen(
            [node, str(script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        stdout_queue: queue.Queue[str] = queue.Queue()
        stderr_queue: queue.Queue[str] = queue.Queue()
        _start_pipe_reader(process.stdout, stdout_queue)
        _start_pipe_reader(process.stderr, stderr_queue)

        try:
            _stdio_send(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "tourism-app", "version": "0.1.0"},
                    },
                },
            )
            if _stdio_read_until_id(stdout_queue, 1, timeout_seconds) is None:
                raise RuntimeError("stdio初始化超时")
            _stdio_send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            _stdio_send(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
            data = _stdio_read_until_id(stdout_queue, 2, timeout_seconds)
            if data is None:
                raise RuntimeError("stdio工具调用超时")
            if data.get("error"):
                raise RuntimeError(str(data["error"]))
            result = data.get("result")
            if isinstance(result, dict):
                result["_transport"] = "stdio"
            print(
                f"[12306-mcp] stdio调用成功：{name} {arguments.get('fromStation')}->{arguments.get('toStation')} {arguments.get('date')}",
                flush=True,
            )
            return result
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            _drain_queue(stderr_queue)

    def _query_interline_candidates(
        self,
        origin: str,
        destination: str,
        travel_date: date | str,
        direct_transport: str,
    ) -> dict[str, Any] | None:
        arguments = {
            "date": _format_date(travel_date),
            "fromStation": origin,
            "toStation": destination,
            "middleStation": "",
            "showWZ": False,
            "trainFilterFlags": "",
            "earliestStartTime": 6,
            "latestStartTime": 23,
            "sortFlag": "startTime",
            "sortReverse": False,
            "limitedNum": 8,
            "format": "json",
        }
        try:
            result = self._call_tool("get-interline-tickets", arguments)
        except Exception:
            return None
        text = _extract_text_content(result)
        interlines = _load_ticket_json(text)
        train_tickets = _interline_ticket_candidates(interlines)
        if not train_tickets:
            return None
        transport = str((result or {}).get("_transport") or direct_transport)
        return {
            "train_tickets": train_tickets,
            "selected_train_index": None,
            "ticket_query_source": "12306_mcp",
            "ticket_query_transport": transport,
            "ticket_query_error": "12306-MCP未查到直达车次，已改用中转余票候选。",
            "notice": "12306-MCP未查到直达车次，已返回中转方案；请选择具体方案后，系统会按最终到达时间重排行程。",
        }


def _mcp_endpoint(raw_url: str) -> str:
    url = (raw_url or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/mcp"):
        return url
    return f"{url}/mcp"


@lru_cache(maxsize=1)
def _find_12306_mcp_script() -> Path | None:
    configured = os.getenv("RAILWAY_MCP_SCRIPT")
    if configured:
        path = Path(configured)
        if path.exists():
            return path

    roots = [
        Path(os.getenv("LOCALAPPDATA", "")) / "npm-cache" / "_npx",
        Path(os.getenv("APPDATA", "")) / "npm" / "node_modules",
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        candidates.extend(root.rglob("node_modules/12306-mcp/build/index.js"))
        direct = root / "12306-mcp" / "build" / "index.js"
        if direct.exists():
            candidates.append(direct)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def _start_pipe_reader(stream: Any, target: queue.Queue[str]) -> None:
    if stream is None:
        return

    def read_lines() -> None:
        for line in stream:
            target.put(line)

    threading.Thread(target=read_lines, daemon=True).start()


def _stdio_send(process: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("stdio输入不可用")
    process.stdin.write(json.dumps(payload, ensure_ascii=True) + "\n")
    process.stdin.flush()


def _stdio_read_until_id(source: queue.Queue[str], message_id: int, timeout_seconds: int) -> dict[str, Any] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            line = source.get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("id") == message_id:
            return data
    return None


def _drain_queue(source: queue.Queue[str]) -> list[str]:
    lines: list[str] = []
    while not source.empty():
        lines.append(source.get_nowait())
    return lines


def _format_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _extract_text_content(result: dict[str, Any] | None) -> str:
    if not result:
        return ""
    content = result.get("content")
    if not isinstance(content, list):
        return ""
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            return str(item.get("text") or "").strip()
    return ""


def _load_ticket_json(text: str) -> list[dict[str, Any]]:
    if not text or text.startswith("Error:") or "没有查询到" in text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _ticket_query_error(text: str) -> str:
    if text.startswith("Error:"):
        return f"12306-MCP已调用，但返回错误：{text[:160]}"
    return "12306-MCP已调用，但未返回可展示直达车次，可能受日期预售期、站点匹配、无直达车或12306接口状态影响。"


def _select_ticket(tickets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    candidates: list[tuple[int, float, int, dict[str, Any], dict[str, Any]]] = []
    for ticket in tickets:
        duration_min = _parse_duration_min(ticket.get("lishi"))
        prices = ticket.get("prices") or []
        if not isinstance(prices, list):
            continue
        for seat in prices:
            if not isinstance(seat, dict) or not _has_available_ticket(seat.get("num")):
                continue
            price = _coerce_price(seat.get("price"))
            if price is None:
                continue
            seat_name = str(seat.get("seat_name") or "")
            priority = 0 if seat_name == "二等座" else 1 if "二等" in seat_name else 2
            candidates.append((priority, price, duration_min, ticket, seat))

    if not candidates:
        return None
    _, _, _, ticket, seat = sorted(candidates, key=lambda item: (item[0], item[1], item[2]))[0]
    return ticket, seat


def _ticket_candidates(tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for ticket in tickets[:12]:
        seats = _seat_candidates(ticket.get("prices") or [])
        best = _best_available_seat(seats)
        one_way_cost = int(round(best["price"])) if best else 0
        candidates.append(
            {
                "train_code": str(ticket.get("start_train_code") or ""),
                "from_station": str(ticket.get("from_station") or ""),
                "to_station": str(ticket.get("to_station") or ""),
                "depart_time": str(ticket.get("start_time") or ""),
                "arrive_time": str(ticket.get("arrive_time") or ""),
                "duration_min": _parse_duration_min(ticket.get("lishi")),
                "duration_text": _duration_text(_parse_duration_min(ticket.get("lishi"))),
                "available": bool(best),
                "seat_type": str((best or {}).get("seat_name") or "暂无可售座席"),
                "ticket_status": str((best or {}).get("status") or "无票"),
                "one_way_cost": one_way_cost,
                "round_trip_cost": one_way_cost * 2 if one_way_cost else 0,
                "seats": seats[:6],
            }
        )
    return candidates


def _interline_ticket_candidates(interlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in interlines[:8]:
        segments = item.get("ticketList") or []
        if not isinstance(segments, list) or not segments:
            continue
        segment_details = []
        total_cost = 0.0
        available = True
        seat_names = []
        for segment in segments:
            if not isinstance(segment, dict):
                available = False
                continue
            seats = _seat_candidates(segment.get("prices") or [])
            best = _best_available_seat(seats)
            if best is None:
                available = False
            else:
                total_cost += float(best["price"])
                seat_names.append(str(best.get("seat_name") or "座席"))
            segment_details.append(
                {
                    "train_code": str(segment.get("start_train_code") or ""),
                    "from_station": str(segment.get("from_station") or ""),
                    "to_station": str(segment.get("to_station") or ""),
                    "depart_time": str(segment.get("start_time") or ""),
                    "arrive_time": str(segment.get("arrive_time") or ""),
                    "duration_text": _duration_text(_parse_duration_min(segment.get("lishi"))),
                    "best_seat": dict(best) if best else None,
                    "seats": seats[:6],
                }
            )
        train_codes = [segment.get("train_code") for segment in segment_details if segment.get("train_code")]
        one_way_cost = int(round(total_cost)) if total_cost else 0
        candidates.append(
            {
                "train_code": "/".join(train_codes),
                "from_station": str(item.get("from_station_name") or segment_details[0].get("from_station") or ""),
                "to_station": str(item.get("end_station_name") or segment_details[-1].get("to_station") or ""),
                "middle_station": str(item.get("middle_station_name") or ""),
                "depart_time": str(item.get("start_time") or segment_details[0].get("depart_time") or ""),
                "arrive_time": str(item.get("arrive_time") or segment_details[-1].get("arrive_time") or ""),
                "duration_min": _parse_duration_min(item.get("lishi")),
                "duration_text": _duration_text(_parse_duration_min(item.get("lishi"))),
                "available": bool(available and one_way_cost),
                "seat_type": " + ".join(seat_names) if seat_names else "暂无可售座席",
                "ticket_status": "有票" if available and one_way_cost else "无票",
                "one_way_cost": one_way_cost,
                "round_trip_cost": one_way_cost * 2 if one_way_cost else 0,
                "transfer": True,
                "transfer_note": f"{item.get('middle_station_name') or '中转站'}换乘，等待{item.get('wait_time') or '以12306为准'}",
                "segments": segment_details,
                "seats": [],
            }
        )
    return candidates


def _seat_candidates(prices: list[Any]) -> list[dict[str, Any]]:
    seats = []
    for seat in prices:
        if not isinstance(seat, dict):
            continue
        price = _coerce_price(seat.get("price"))
        if price is None:
            continue
        status = str(seat.get("num") or "").strip() or "未知"
        seats.append(
            {
                "seat_name": str(seat.get("seat_name") or "座席"),
                "status": status,
                "available": _has_available_ticket(status),
                "price": round(price, 1),
            }
        )
    return seats


def _best_available_seat(seats: list[dict[str, Any]]) -> dict[str, Any] | None:
    available = [seat for seat in seats if seat.get("available")]
    if not available:
        return None
    return sorted(available, key=lambda seat: (_seat_priority(str(seat.get("seat_name") or "")), float(seat["price"])))[0]


def _seat_priority(seat_name: str) -> int:
    if seat_name == "二等座":
        return 0
    if "二等" in seat_name:
        return 1
    if "硬座" in seat_name or "无座" in seat_name:
        return 2
    if "一等" in seat_name:
        return 3
    return 4


def _selected_train_index(candidates: list[dict[str, Any]], ticket: dict[str, Any], seat: dict[str, Any]) -> int | None:
    train_code = str(ticket.get("start_train_code") or "")
    seat_name = str(seat.get("seat_name") or "")
    for index, candidate in enumerate(candidates):
        if candidate.get("train_code") == train_code and candidate.get("seat_type") == seat_name:
            return index
    return None


def _has_available_ticket(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.isdigit():
        return int(text) > 0
    return text in {"有", "充足", "有票"}


def _coerce_price(value: Any) -> float | None:
    try:
        price = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return price if price > 0 else None


def _parse_duration_min(value: Any) -> int:
    text = str(value or "").strip()
    match = re.match(r"^(\d{1,2}):(\d{1,2})$", text)
    if not match:
        return 0
    return int(match.group(1)) * 60 + int(match.group(2))


def _duration_text(duration_min: int) -> str:
    if not duration_min:
        return "时长待确认"
    hours = duration_min // 60
    minutes = duration_min % 60
    if hours and minutes:
        return f"{hours}小时{minutes}分钟"
    if hours:
        return f"{hours}小时"
    return f"{minutes}分钟"
