from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

OUTPUT = Path("output")

# 你想看的城市（广东省内）
TARGET_CITIES = {"广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州"}


def is_relevant(job: dict) -> bool:
    """筛选规则：广东 或 远程，且跟 AI/技术相关。"""
    loc_ok = job.get("remote") or (job.get("city") in TARGET_CITIES)
    if not loc_ok:
        return False
    if job.get("is_ai_related"):
        return True
    skills = " ".join(job.get("skills") or []).lower()
    return any(k in skills for k in ("python", "llm", "rag", "fastapi", "agent"))


def build_markdown(jobs: list[dict], total: int) -> str:
    picked = [j for j in jobs if is_relevant(j)]
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# 岗位日报 · {today}",
        "",
        f"抓取 {total} 条，结构化 {len(jobs)} 条，命中 {len(picked)} 条。",
        "",
    ]

    if not picked:
        lines.append("今天没有符合条件的新岗位。")
        return "\n".join(lines)

    lines += [
        "| # | 标题 | 城市 | 远程 | 薪资 | 技能 |",
        "|---|---|---|---|---|---|",
    ]
    for i, j in enumerate(picked, start=1):
        city = j.get("city") or "-"
        remote = "是" if j.get("remote") else ""
        skills = "、".join((j.get("skills") or [])[:4]) or "-"
        title = (j.get("title") or "")[:32]
        link = j.get("url") or ""
        title_md = f"[{title}]({link})" if link else title
        lines.append(
            f"| {i} | {title_md} | {city} | {remote} | {j.get('salary') or '-'} | {skills} |"
        )

    lines += ["", "## 一句话概括", ""]
    for j in picked:
        lines.append(f"- **{j.get('title', '')[:24]}**：{j.get('summary', '')}")

    return "\n".join(lines)


def build_excel(jobs: list[dict], path: Path) -> None:
    picked = [j for j in jobs if is_relevant(j)]
    wb = Workbook()
    ws = wb.active
    ws.title = "岗位"

    headers = ["标题", "公司", "城市", "远程", "薪资", "技能", "AI相关", "概括", "链接"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for j in picked:
        ws.append([
            j.get("title"),
            j.get("company"),
            j.get("city"),
            "是" if j.get("remote") else "",
            j.get("salary"),
            "、".join(j.get("skills") or []),
            "是" if j.get("is_ai_related") else "",
            j.get("summary"),
            j.get("url"),
        ])

    widths = [40, 18, 10, 8, 12, 28, 10, 36, 40]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    wb.save(path)


def write_reports(jobs: list[dict], total: int) -> tuple[Path, Path]:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # 双保险：即使调用方误传空结果，也不要把已有日报覆盖成空的
    if not jobs:
        md, xlsx = OUTPUT / "latest.md", OUTPUT / "latest.xlsx"
        if md.exists() and xlsx.exists():
            print("[report] 无结构化结果，跳过写入，保留已有日报")
            return md, xlsx

    today = datetime.now().strftime("%Y-%m-%d")

    md_path = OUTPUT / f"report-{today}.md"
    md_path.write_text(build_markdown(jobs, total), encoding="utf-8")

    # 固定文件名，方便每天覆盖，也方便 Actions 提交
    latest = OUTPUT / "latest.md"
    latest.write_text(build_markdown(jobs, total), encoding="utf-8")

    xlsx_path = OUTPUT / f"jobs-{today}.xlsx"
    build_excel(jobs, xlsx_path)
    build_excel(jobs, OUTPUT / "latest.xlsx")

    return md_path, xlsx_path