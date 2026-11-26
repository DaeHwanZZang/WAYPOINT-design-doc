#!/usr/bin/env python3
"""FMS 웹 화면 캡처 (Chrome DevTools Protocol).

설계서/v1.1 에서:  ../../AMR-fms/.venv/bin/python tools/shoot.py shots.json
shots.json: [{"name": "map", "url": "http://127.0.0.1:8765/#map", "wait": 3, "js": "..."}]
결과: assets/screens/{name}.png
"""
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "assets" / "screens"
PORT = 9333


async def run(shots, width=1600, height=1000):
    OUT.mkdir(parents=True, exist_ok=True)
    prof = tempfile.mkdtemp(prefix="shoot-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", "--disable-gpu",
                             f"--user-data-dir={prof}", f"--window-size={width},{height}",
                             "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except Exception:
                time.sleep(0.2)
        page = next(t for t in tabs if t["type"] == "page")
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=64 * 2**20) as ws:
            seq = 0

            async def call(method, **params):
                nonlocal seq
                seq += 1
                my = seq
                await ws.send(json.dumps({"id": my, "method": method, "params": params}))
                while True:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), 30))
                    if msg.get("method") == "Page.javascriptDialogOpening":
                        # 편집 중 페이지 이동 확인창 등은 수락한다
                        await ws.send(json.dumps({"id": 10**6 + my, "method": "Page.handleJavaScriptDialog",
                                                  "params": {"accept": True}}))
                        continue
                    if msg.get("id") == my:
                        if "error" in msg:
                            raise RuntimeError(f"{method}: {msg['error']}")
                        return msg.get("result", {})

            await call("Page.enable")
            await call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                       deviceScaleFactor=1.5, mobile=False)
            for shot in shots:
                w, h = shot.get("width", width), shot.get("height", height)
                await call("Emulation.setDeviceMetricsOverride", width=w, height=h,
                           deviceScaleFactor=1.5, mobile=False)
                if shot.get("url"):
                    await call("Page.navigate", url=shot["url"])
                await asyncio.sleep(shot.get("wait", 3))
                for js in shot.get("steps", []):
                    if isinstance(js, (int, float)):
                        await asyncio.sleep(js)
                        continue
                    r = await call("Runtime.evaluate", expression=js, awaitPromise=True)
                    if r.get("exceptionDetails"):
                        print("  JS 오류:", shot["name"], r["exceptionDetails"].get("text"),
                              r["exceptionDetails"].get("exception", {}).get("description", "")[:200])
                await asyncio.sleep(shot.get("after", 1.0))
                params = {"format": "png"}
                if shot.get("clip"):
                    x, y, cw, ch = shot["clip"]
                    params["clip"] = {"x": x, "y": y, "width": cw, "height": ch, "scale": 1}
                data = await call("Page.captureScreenshot", **params)
                (OUT / f"{shot['name']}.png").write_bytes(base64.b64decode(data["data"]))
                print("saved", shot["name"], flush=True)
    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(run(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))))
