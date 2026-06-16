import datetime
import json
import os
import re
import socket
import subprocess
import sys
import time

import requests
import websocket


CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME):
    CHROME = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

PROFILE = r"C:\Temp\chrome_headless"


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_debugger(debug_url):
    for _ in range(20):
        try:
            targets = requests.get(debug_url, timeout=2).json()
            pages = [target for target in targets if target.get("type") == "page"]
            if pages:
                return pages[0]
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError("Chrome debugging endpoint did not start")


def find_existing_debugger():
    try:
        targets = requests.get("http://127.0.0.1:9222/json", timeout=2).json()
        pages = [target for target in targets if target.get("type") == "page"]
        return pages[0] if pages else None
    except requests.RequestException:
        return None


def close_existing_debugger():
    page = find_existing_debugger()
    if page is None:
        return
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=5,
        suppress_origin=True,
    )
    try:
        ws.send(json.dumps({"id": 99, "method": "Browser.close"}))
    finally:
        ws.close()
    time.sleep(1)


def open_login_browser():
    close_existing_debugger()
    subprocess.Popen([
        CHROME,
        f"--user-data-dir={PROFILE}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://platform.deepseek.com/usage",
    ])


def read_usage_page(page):
    ws = websocket.create_connection(
        page["webSocketDebuggerUrl"],
        timeout=10,
        suppress_origin=True,
    )
    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": "https://platform.deepseek.com/usage"},
        }))
        time.sleep(7)
        ws.send(json.dumps({
            "id": 2,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.body.innerText",
                "returnByValue": True,
            },
        }))
        deadline = time.time() + 8
        while time.time() < deadline:
            ws.settimeout(max(0.5, deadline - time.time()))
            message = json.loads(ws.recv())
            if message.get("id") == 2:
                return (
                    message.get("result", {})
                    .get("result", {})
                    .get("value", "")
                )
    finally:
        ws.close()
    return ""


def parse_model_usage(text, model="deepseek-v4-pro"):
    if not text or model not in text:
        if "\u767b\u5f55" in text or "\u6ce8\u518c" in text:
            raise RuntimeError("Login expired; run login_deepseek.vbs")
        raise RuntimeError("DeepSeek usage page format has changed")

    chunk = text.split(model, 1)[1]
    for next_model in ("deepseek-v4-flash", "deepseek-chat", "deepseek-reasoner"):
        if next_model in chunk:
            chunk = chunk.split(next_model, 1)[0]

    token_match = re.search(r"Tokens\s*\n\s*([\d,]+)", chunk, re.IGNORECASE)
    request_match = re.search(
        r"(?:API[^\n]*|Requests?)\s*\n\s*([\d,]+)",
        chunk,
        re.IGNORECASE,
    )
    tokens = int(token_match.group(1).replace(",", "")) if token_match else 0
    requests_count = (
        int(request_match.group(1).replace(",", "")) if request_match else 0
    )

    number = r"([\d,]+(?:\.\d+)?)"
    cost_patterns = [
        rf"(?:Cost|Amount|Spend|"
        rf"\u8d39\u7528|\u6d88\u8d39|\u91d1\u989d|\u82b1\u8d39)"
        rf"[^\d]{{0,30}}{number}",
        rf"(?:CNY|RMB|\u00a5|\uffe5)[ \t]*{number}",
        rf"{number}[ \t]*(?:CNY|RMB|\u5143)",
    ]
    cost = None
    for pattern in cost_patterns:
        match = re.search(pattern, chunk, re.IGNORECASE)
        if match:
            cost = float(match.group(1).replace(",", ""))
            break

    if cost is None:
        # DeepSeek currently renders the cost summary outside the model block.
        # Preserve page order: the second amount is the model cost on this view.
        page_amounts = re.findall(
            rf"{number}[ \t]*(?:CNY|RMB|\u5143)",
            text,
            re.IGNORECASE,
        )
        if not page_amounts:
            page_amounts = re.findall(
                rf"(?:CNY|RMB|\u00a5|\uffe5)[ \t]*{number}",
                text,
                re.IGNORECASE,
            )
        if page_amounts:
            selected = page_amounts[1] if len(page_amounts) > 1 else page_amounts[0]
            cost = float(selected.replace(",", ""))
        else:
            cost = 0.0

    if not tokens:
        raise RuntimeError("Could not parse monthly token usage")
    return requests_count, tokens, cost


def save_usage(requests_count, tokens, cost):
    today = datetime.date.today().isoformat()
    usage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "deepseek_usage.json")
    data = {
        today: {
            "month_requests": requests_count,
            "month_tokens": tokens,
            "month_cost": cost,
            "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    }
    with open(usage_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def main():
    if not os.path.exists(CHROME):
        raise RuntimeError("Google Chrome was not found")

    chrome = None
    try:
        page = find_existing_debugger()
        if page is None:
            debug_port = find_free_port()
            chrome = subprocess.Popen(
                [
                    CHROME,
                    "--headless=new",
                    f"--remote-debugging-port={debug_port}",
                    "--remote-allow-origins=*",
                    f"--user-data-dir={PROFILE}",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--window-size=1920,1080",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            page = wait_for_debugger(f"http://127.0.0.1:{debug_port}/json")
        text = read_usage_page(page)
        requests_count, tokens, cost = parse_model_usage(text)
        save_usage(requests_count, tokens, cost)
        print(
            f"Updated: {requests_count} requests, "
            f"{tokens:,} tokens, CNY {cost:.2f}"
        )
    finally:
        if chrome is not None and chrome.poll() is None:
            chrome.terminate()
            try:
                chrome.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome.kill()


if __name__ == "__main__":
    if "--login" in sys.argv:
        open_login_browser()
        print("Opened DeepSeek login browser")
        raise SystemExit(0)
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(1)
