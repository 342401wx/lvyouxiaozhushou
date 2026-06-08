import argparse
import os
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _bootstrap import ROOT, SRC  # noqa: F401


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start tourism app and optional 12306-MCP in one command.")
    parser.add_argument("--host", default="127.0.0.1", help="Tourism app host.")
    parser.add_argument("--port", type=int, default=7860, help="Tourism app port.")
    parser.add_argument("--railway-host", default="127.0.0.1", help="12306-MCP host.")
    parser.add_argument("--railway-port", type=int, default=8765, help="12306-MCP port.")
    parser.add_argument("--skip-railway", action="store_true", help="Start only the tourism app.")
    parser.add_argument("--railway-wait", type=int, default=45, help="Seconds to wait for 12306-MCP readiness.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    railway_process: subprocess.Popen | None = None
    railway_url = f"http://{args.railway_host}:{args.railway_port}"

    try:
        if not args.skip_railway:
            railway_process = start_railway_mcp(args.railway_host, args.railway_port)
            if railway_process:
                os.environ["RAILWAY_PROVIDER"] = "12306_mcp"
                os.environ["RAILWAY_MCP_URL"] = railway_url
                print(f"正在等待 12306-MCP 就绪：{railway_url}/mcp")
                if wait_for_mcp(railway_url, args.railway_wait):
                    print("12306-MCP 已就绪，高铁/火车预算会优先查询参考票价。")
                else:
                    print("12306-MCP 暂未就绪，小助手会先使用兜底估算；首次 npx 下载可能需要更久。")

        print(f"旅游规划小助手即将启动：http://{args.host}:{args.port}")
        from education_qa.web_app import run_server

        run_server(host=args.host, port=args.port)
    finally:
        stop_process(railway_process)


def start_railway_mcp(host: str, port: int) -> subprocess.Popen | None:
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        print("未找到 npx，无法启动 12306-MCP；小助手会使用城际交通兜底估算。")
        return None

    command = [npx, "-y", "12306-mcp", "--host", host, "--port", str(port)]
    print("正在启动 12306-MCP：npx -y 12306-mcp --host " f"{host} --port {port}")
    return subprocess.Popen(command, cwd=str(ROOT))


def wait_for_mcp(base_url: str, timeout_seconds: int) -> bool:
    deadline = time.time() + max(0, timeout_seconds)
    while time.time() < deadline:
        try:
            request = Request(f"{base_url.rstrip('/')}/mcp", method="GET")
            with urlopen(request, timeout=2):
                return True
        except HTTPError as exc:
            if exc.code == 405:
                return True
        except (OSError, URLError):
            pass
        time.sleep(1)
    return False


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    print("正在停止 12306-MCP...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


if __name__ == "__main__":
    main()
