from dotenv import load_dotenv
load_dotenv()

import json
import os
import time

from openai import OpenAI
from pydantic import ValidationError

from models import ExtractionResult

MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")

BATCH_SIZE = 8
MAX_RETRIES = 2

SYSTEM_PROMPT = """你是招聘信息抽取器，把招聘帖转成 JSON。

规则：
1. 只输出 JSON 对象，形如 {"jobs": [ ... ]}，不要解释、不要 markdown 代码块
2. 每个 job 必须包含：
   source_id, title, company, city, remote, salary, skills, is_ai_related, summary
3. 帖子里没有的信息填 null，绝对不要猜
4. remote：明确写了远程/可远程/全远程 → true，否则 false
5. city：只填城市名（深圳、广州、北京…），没写就是 null
6. skills：只填帖子里明确出现的技术名词，最多 8 个
7. is_ai_related：岗位职责是否涉及 AI / 大模型 / 机器学习。
   只是"了解 AI 优先"不算；数据标注不算
8. summary：不超过 30 字
9. jobs 数组长度必须和输入条目数完全一致，source_id 要原样带回"""

FEW_SHOT_USER = """【待抽取】
[{"id":"jobs-1","title":"深圳｜AI 应用开发","content":"负责 RAG 知识库开发，熟悉 Python、FastAPI，15-25K，可远程。"}]

【问题】上面的 id 列表：jobs-1"""


def _client() -> OpenAI:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("没有配置 DEEPSEEK_API_KEY")
    return OpenAI(api_key=key, base_url=BASE_URL, timeout=60)


def _payload(batch: list[dict]) -> str:
    rows = [
        {"id": it["id"], "title": it["title"], "content": it["content"]}
        for it in batch
    ]
    return json.dumps(rows, ensure_ascii=False)


def extract_batch(client: OpenAI, batch: list[dict]) -> list[dict]:
    """抽一批。失败返回空列表，由上层决定怎么处理。"""
    user = f"【待抽取】\n{_payload(batch)}"
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
                temperature=0,
                max_tokens=2000,
            )
            raw = (resp.choices[0].message.content or "").strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

            data = json.loads(raw)
            result = ExtractionResult.model_validate(data)
            return [job.model_dump() for job in result.jobs]

        except (json.JSONDecodeError, ValidationError) as exc:
            last_err = exc
            print(f"    第 {attempt} 批抽取失败：{str(exc)[:100]}")
            time.sleep(1.0 * attempt)

    print(f"    [WARN] 这批 {len(batch)} 条放弃：{last_err}")
    return []


def extract_all(items: list[dict]) -> list[dict]:
    client = _client()
    out: list[dict] = []

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        print(f"[extract] 第 {i // BATCH_SIZE + 1} 批，{len(batch)} 条")
        jobs = extract_batch(client, batch)
        out.extend(jobs)

    # 补回原始 url（模型不需要知道 url，但我们报告里要用）
    url_map = {it["id"]: it["url"] for it in items}
    for job in out:
        job["url"] = url_map.get(job["source_id"], "")

    print(f"[extract] 成功抽取 {len(out)}/{len(items)} 条")
    return out