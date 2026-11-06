# day19-jobfeed · 岗位监控自动化

每天抓 V2EX 酷工作 / 远程节点的公开帖子，用大模型把正文结构化成城市、是否远程、技能栈、薪资等字段，按「广东省内或远程 + AI 相关」筛选，生成 Markdown 日报和 Excel。

## 本地运行

```powershell
uv sync
# 在 .env 里填 DEEPSEEK_API_KEY（.env 不入库）
uv run main.py            # 跑全流程
uv run test_extract.py    # 只看 AI 结构化结果
```

网络不通时 `fetch.py` 会自动降级到 `samples/topics.json` 的 5 条样本，保证 demo 永远能跑。

## 去重与幂等

`state.json` 记录已处理的帖子 id。第二次跑如果「新帖 0 条」，会**跳过结构化（不调 API、不花钱），也不重写报告** —— 保留已有的 `latest.md` / `latest.xlsx`。这是定时任务不重复烧钱的关键。

## 产物

```
output/
├── latest.md / latest.xlsx                       固定文件名，每天覆盖，供 Actions 提交
└── report-YYYY-MM-DD.md / jobs-YYYY-MM-DD.xlsx  带日期的历史快照
```

## 定时（GitHub Actions）

`.github/workflows/daily.yml`：每天 UTC 0:00（北京 08:00）自动跑，把 `output/` 和 `state.json` 提交回仓库。也可以手动 Run workflow 触发。

上线前需在仓库 **Settings → Secrets and variables → Actions** 配置 `DEEPSEEK_API_KEY`，值绝不能写进 workflow 文件。

注意两点：cron 按 UTC 算；仓库 60 天无任何提交时 GitHub 会自动停用 schedule，每周随手 commit 一次即可。

## 目录

| 文件 | 职责 |
|---|---|
| `models.py` | pydantic 数据结构，校验模型输出 |
| `fetch.py` | V2EX 公开 API 抓取 + 本地样本兜底 |
| `extract.py` | 批量调 DeepSeek 做结构化（每批 8 条，重试 2 次） |
| `report.py` | Markdown + Excel 报告 |
| `main.py` | 编排、去重、状态落盘 |
