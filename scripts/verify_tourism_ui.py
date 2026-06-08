from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

try:
    import websocket
except ImportError as exc:  # pragma: no cover - local verification helper
    raise SystemExit("websocket-client is required for this UI verification helper.") from exc


CHROME_PATHS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
]


def _chrome_path() -> Path:
    for path in CHROME_PATHS:
        if path.exists():
            return path
    raise SystemExit("Chrome or Edge was not found.")


def _devtools_pages(port: int) -> list[dict]:
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1))


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7860/?demo=1"
    port = 9333
    chrome = _chrome_path()
    proc = subprocess.Popen(
        [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={port}",
            r"--user-data-dir=C:\tmp\chrome-tourism-devtools",
            "--window-size=1600,1000",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        pages = []
        for _ in range(40):
            try:
                pages = _devtools_pages(port)
                if pages:
                    break
            except Exception:
                time.sleep(0.25)
        if not pages:
            raise RuntimeError("Chrome DevTools endpoint did not open.")

        target = next((page for page in pages if "127.0.0.1:7860" in page.get("url", "")), pages[0])
        ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=5)
        counter = 0

        def call(method: str, params: dict | None = None) -> dict:
            nonlocal counter
            counter += 1
            ws.send(json.dumps({"id": counter, "method": method, "params": params or {}}))
            while True:
                message = json.loads(ws.recv())
                if message.get("id") == counter:
                    return message

        call("Runtime.enable")
        for _ in range(60):
            ready = call(
                "Runtime.evaluate",
                {"expression": "!!document.querySelector('.detail-btn')", "returnByValue": True},
            )
            if ready["result"]["result"].get("value"):
                break
            time.sleep(0.5)

        expression = r"""
(() => {
  const detailButton = document.querySelector('.detail-btn');
  if (!detailButton) return { ok: false, stage: 'detail-button-missing' };
  detailButton.click();
  const stopTitle = document.querySelector('#drawer-content h2')?.textContent || '';
  const hotelButtons = Array.from(document.querySelectorAll('[data-hotel-index]'));
  if (!hotelButtons.length) return { ok: false, stage: 'hotel-buttons-missing', stopTitle };
  hotelButtons[0].click();
  const hotelTitle = document.querySelector('#drawer-content h2')?.textContent || '';
  const backButton = !!document.querySelector('#hotel-back');
  const hotelText = document.querySelector('#drawer-content')?.textContent || '';
  return {
    ok: backButton && hotelText.includes('酒店信息') && hotelText.includes('价格'),
    stopTitle,
    hotelTitle,
    hotels: hotelButtons.length,
    backButton,
    hasHotelInfo: hotelText.includes('酒店信息'),
    hasPrice: hotelText.includes('价格')
  };
})()
"""
        result = call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
        value = result["result"]["result"].get("value")
        print(json.dumps(value, ensure_ascii=False, indent=2))
        ws.close()
        return 0 if value and value.get("ok") else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
