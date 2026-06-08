from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .app_config import get_config
from .auth_store import AuthStore, summarize_intent, summarize_plan
from .intent_parser import parse_travel_intent
from .paths import PROJECT_ROOT, TOURISM_VECTORSTORE_PATH
from .trip_planner import TourismTripPlanner


WEB_DIR = PROJECT_ROOT / "web"
SESSION_COOKIE = "tourism_session"
_PLANNER: TourismTripPlanner | None = None
_PLANNER_LOCK = threading.Lock()
_AUTH = AuthStore()
_CONFIG = get_config()
_PLAN_SEMAPHORE = threading.BoundedSemaphore(_CONFIG.plan_concurrency)
_INTENT_SEMAPHORE = threading.BoundedSemaphore(_CONFIG.intent_concurrency)


def get_planner() -> TourismTripPlanner:
    global _PLANNER
    if _PLANNER is None:
        with _PLANNER_LOCK:
            if _PLANNER is None:
                _PLANNER = TourismTripPlanner(config=_CONFIG)
    return _PLANNER


class PooledThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def __init__(self, server_address, RequestHandlerClass, *, max_workers: int, request_queue_size: int):
        self.request_queue_size = request_queue_size
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tourism-http")
        super().__init__(server_address, RequestHandlerClass)

    def process_request(self, request, client_address) -> None:
        try:
            self._executor.submit(self.process_request_thread, request, client_address)
        except RuntimeError:
            self.shutdown_request(request)

    def server_close(self) -> None:
        super().server_close()
        self._executor.shutdown(wait=True, cancel_futures=False)


class TourismAppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[tourism-app] {format % args}")

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/auth/me":
            user = self._current_user()
            self._send_json({"authenticated": bool(user), "user": _public_user(user)})
            return

        if path == "/api/memory":
            user = self._require_user()
            if user is None:
                return
            self._send_json({"success": True, "data": _AUTH.list_memories(user["id"])})
            return

        if path.startswith("/api/memory/"):
            user = self._require_user()
            if user is None:
                return
            memory_id_text = path[len("/api/memory/") :].strip("/")
            if not memory_id_text.isdigit():
                self._send_json({"success": False, "message": "记忆编号不正确。"}, status=400)
                return
            memory = _AUTH.get_memory(user["id"], int(memory_id_text))
            if memory is None:
                self._send_json({"success": False, "message": "未找到这条记忆。"}, status=404)
                return
            payload = memory.get("payload")
            if isinstance(payload, dict) and isinstance(payload.get("plan"), dict):
                get_planner().refresh_plan_rag_context(payload["plan"])
            self._send_json({"success": True, "data": memory})
            return

        if path == "/api/config":
            config = get_config()
            self._send_json(
                {
                    "amap_js_key": config.amap_js_key,
                    "amap_security_js_code": config.amap_security_js_code,
                    "has_amap_web_service": config.has_amap_web_service,
                    "has_deepseek": config.has_deepseek,
                    "has_12306_mcp": config.has_12306_mcp,
                    "has_realtime_intercity": config.has_realtime_intercity,
                    "has_realtime_scenic_status": config.has_realtime_scenic_status,
                    "has_search_api": config.has_search_api,
                    "search_provider": config.search_provider,
                    "has_tourism_index": TOURISM_VECTORSTORE_PATH.exists(),
                    "examples": {
                        "city": "成都",
                        "interests": ["历史", "美食", "观光"],
                    },
                }
            )
            return

        if path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "index": str(TOURISM_VECTORSTORE_PATH),
                    "concurrency": {
                        "http_max_workers": _CONFIG.http_max_workers,
                        "http_request_queue_size": _CONFIG.http_request_queue_size,
                        "plan_concurrency": _CONFIG.plan_concurrency,
                        "intent_concurrency": _CONFIG.intent_concurrency,
                        "sqlite_timeout": _CONFIG.sqlite_timeout,
                    },
                }
            )
            return

        if path in {"/", ""}:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/auth/register":
            payload = self._read_json()
            user, error = _AUTH.register(str(payload.get("username") or ""), str(payload.get("password") or ""))
            if error:
                self._send_json({"success": False, "message": error}, status=400)
                return
            token, expires = _AUTH.create_session(user["id"])
            self._send_json(
                {"success": True, "message": "注册成功", "user": _public_user(user)},
                cookies=[_session_cookie(token, expires)],
            )
            return

        if path == "/api/auth/login":
            payload = self._read_json()
            user, error = _AUTH.login(str(payload.get("username") or ""), str(payload.get("password") or ""))
            if error:
                self._send_json({"success": False, "message": error}, status=401)
                return
            token, expires = _AUTH.create_session(user["id"])
            self._send_json(
                {"success": True, "message": "登录成功", "user": _public_user(user)},
                cookies=[_session_cookie(token, expires)],
            )
            return

        if path == "/api/auth/logout":
            _AUTH.delete_session(self._session_token())
            self._send_json(
                {"success": True, "message": "已退出登录"},
                cookies=[f"{SESSION_COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"],
            )
            return

        if path == "/api/intent":
            user = self._require_user()
            if user is None:
                return
            if not _INTENT_SEMAPHORE.acquire(timeout=2):
                self._send_json({"success": False, "message": "当前识别请求较多，请稍后再试。"}, status=503)
                return
            try:
                payload = self._read_json()
                text = str(payload.get("text") or payload.get("message") or "")
                intent = parse_travel_intent(text)
                title, summary = summarize_intent(intent)
                _AUTH.add_memory(user["id"], "intent", title, summary, {"text": text, "intent": intent})
                self._send_json({"success": True, "message": "识别完成", "data": intent})
            except Exception as exc:  # pragma: no cover - covered through manual app use
                self._send_json({"success": False, "message": f"识别失败：{exc}"}, status=500)
            finally:
                _INTENT_SEMAPHORE.release()
            return

        if path == "/api/intercity-options":
            user = self._require_user()
            if user is None:
                return
            if not _INTENT_SEMAPHORE.acquire(timeout=2):
                self._send_json({"success": False, "message": "当前交通查询请求较多，请稍后再试。"}, status=503)
                return
            try:
                payload = self._read_json()
                self._send_json(get_planner().preview_intercity(payload))
            except Exception as exc:  # pragma: no cover - covered through manual app use
                self._send_json({"success": False, "message": f"城际交通查询失败：{exc}"}, status=500)
            finally:
                _INTENT_SEMAPHORE.release()
            return

        if path != "/api/plan":
            self.send_error(404, "Not found")
            return

        user = self._require_user()
        if user is None:
            return
        if not _PLAN_SEMAPHORE.acquire(timeout=2):
            self._send_json({"success": False, "message": "当前生成攻略的人较多，请稍后再试。"}, status=503)
            return
        try:
            payload = self._read_json()
            result = get_planner().plan(payload)
            if result.get("success") and isinstance(result.get("data"), dict):
                title, summary = summarize_plan(result["data"])
                _AUTH.add_memory(user["id"], "plan", title, summary, {"request": payload, "plan": result["data"]})
            self._send_json(result)
        except Exception as exc:  # pragma: no cover - covered through manual app use
            self._send_json(
                {
                    "success": False,
                    "message": f"规划失败：{exc}",
                },
                status=500,
            )
        finally:
            _PLAN_SEMAPHORE.release()

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _send_json(
        self,
        payload: dict[str, Any],
        *,
        status: int = 200,
        cookies: list[str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _require_user(self) -> dict[str, Any] | None:
        user = self._current_user()
        if user is None:
            self._send_json({"success": False, "message": "请先登录。"}, status=401)
        return user

    def _current_user(self) -> dict[str, Any] | None:
        return _AUTH.user_from_session(self._session_token())

    def _session_token(self) -> str:
        cookie_header = self.headers.get("Cookie", "")
        for part in cookie_header.split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE:
                return value
        return ""


def _session_cookie(token: str, expires: datetime) -> str:
    expires_text = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return (
        f"{SESSION_COOKIE}={token}; Path=/; Max-Age={7 * 24 * 60 * 60}; "
        f"Expires={expires_text}; HttpOnly; SameSite=Lax"
    )


def _public_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user:
        return None
    return {"id": user["id"], "username": user["username"]}


def run_server(host: str = "127.0.0.1", port: int = 7860) -> ThreadingHTTPServer:
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    config = _CONFIG
    server = PooledThreadingHTTPServer(
        (host, port),
        TourismAppHandler,
        max_workers=config.http_max_workers,
        request_queue_size=config.http_request_queue_size,
    )
    print(f"旅游规划小助手已启动：http://{host}:{port}", flush=True)
    print(
        "并发配置："
        f"HTTP线程={config.http_max_workers}，连接队列={config.http_request_queue_size}，"
        f"攻略生成={config.plan_concurrency}，需求识别/交通查询={config.intent_concurrency}，"
        f"SQLite等待={config.sqlite_timeout}s。",
        flush=True,
    )
    print("按 Ctrl+C 停止服务。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("正在停止服务...")
    finally:
        server.server_close()
    return server
