import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from extract import extract_all
from fetch import fetch_all
from report import write_reports

load_dotenv()

STATE = Path("state.json")


def load_state() -> dict:
    if not STATE.exists():
        return {"seen_ids": [], "jobs": []}
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        data.setdefault("seen_ids", [])
        data.setdefault("jobs", [])
        return data
    except json.JSONDecodeError:
        return {"seen_ids": [], "jobs": []}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    state = load_state()
    seen = set(state.get("seen_ids", []))
    # 累计所有已结构化的岗位。报告展示的是「至今抓到的全部岗位」，
    # 不是「本次新帖」—— 否则某天只来 1 条新帖（或不匹配），
    # 重新生成报告就会把之前命中的岗位全冲掉。
    all_jobs: list[dict] = list(state.get("jobs", []))

    items = fetch_all()
    if not items:
        print("没有抓到任何数据，退出")
        return 1

    fresh = [it for it in items if it["id"] not in seen]
    print(f"[main] 抓取 {len(items)} 条，其中新帖 {len(fresh)} 条")

    if fresh:
        new_jobs = extract_all(fresh)
        by_id = {j.get("source_id"): j for j in all_jobs}
        for j in new_jobs:
            by_id[j.get("source_id")] = j
        all_jobs = list(by_id.values())
        state["jobs"] = all_jobs
        print(f"[main] 累计已结构化 {len(all_jobs)} 条")
    else:
        print("[main] 没有新帖，跳过结构化（省钱）")

    if all_jobs:
        md_path, xlsx_path = write_reports(all_jobs, len(items))
        print(f"[main] Markdown：{md_path}")
        print(f"[main] Excel：{xlsx_path}")
    else:
        print("[main] 暂无结构化结果，保留已有日报")

    state["seen_ids"] = sorted(seen | {it["id"] for it in items})
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
