import json
import time
from pathlib import Path

import httpx

API = "https://www.v2ex.com/api/topics/show.json"
NODES = ["jobs", "remote"]
UA = "Mozilla/5.0 (compatible; jobfeed/1.0; personal use)"
FALLBACK = Path("samples/topics.json")

MAX_CONTENT = 600          # 正文截断，省 token


def _normalize(raw: dict, node: str) -> dict:
    """把 V2EX 的返回压成我们关心的字段。"""
    return {
        "id": f"{node}-{raw.get('id')}",
        "title": (raw.get("title") or "").strip(),
        "url": raw.get("url") or "",
        "content": (raw.get("content") or "")[:MAX_CONTENT],
        "created": raw.get("created"),
    }


def fetch_node(node: str, timeout: float = 15.0) -> list[dict]:
    try:
        resp = httpx.get(
            API,
            params={"node_name": node},
            headers={"User-Agent": UA},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:                      # noqa: BLE001
        print(f"[fetch] {node} 失败：{exc}")
        return []

    if not isinstance(data, list):
        print(f"[fetch] {node} 返回格式异常")
        return []

    return [_normalize(item, node) for item in data]


def fetch_all() -> list[dict]:
    """抓所有节点；全失败就用本地样本。"""
    all_items: list[dict] = []
    for node in NODES:
        items = fetch_node(node)
        print(f"[fetch] {node}：{len(items)} 条")
        all_items.extend(items)
        time.sleep(1.0)                           # 礼貌延迟

    if not all_items:
        if FALLBACK.exists():
            print(f"[fetch] 全部失败，使用本地样本 {FALLBACK}")
            all_items = json.loads(FALLBACK.read_text(encoding="utf-8"))
        else:
            print("[fetch] 全部失败，且没有样本文件")
            return []

    # 按 id 去重（同一帖可能跨节点）
    seen: set[str] = set()
    unique: list[dict] = []
    for item in all_items:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique.append(item)
    return unique


if __name__ == "__main__":
    items = fetch_all()
    print(f"\n共 {len(items)} 条")
    for it in items[:3]:
        print(f"  {it['id']}  {it['title']}")