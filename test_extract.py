import json
from pathlib import Path

from extract import extract_all

items = json.loads(Path("samples/topics.json").read_text(encoding="utf-8"))
jobs = extract_all(items)

for j in jobs:
    print(f"\n{j['title']}")
    print(f"  城市={j['city']}  远程={j['remote']}  AI={j['is_ai_related']}")
    print(f"  技能={j['skills']}  薪资={j['salary']}")
    print(f"  概括={j['summary']}")