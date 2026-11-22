# Reddit 赌博问题讨论 — 原帖核实及开发 QA 输入（2026-11-22）

以下三条是 **真实 Reddit 原帖（有回复、至少一个楼中楼）** 的候选参考。阅读公开页面不构成允许整篇重新发布或批量自动抓取的许可。Reddit 用户保留内容权利，重用必须满足 Reddit 协议及原作者授权。不可在本站假冒原作者、引用未获授权的全文和评论。

| 原帖 | Reddit 原帖 ID | 已见到的结构 |
|---|---|---|
| 戒赌约 1000 天后复赌 | 1jf6n1r | 楼主正文、多个真实评论及楼主对评论的回复 |
| What's usually happening right before you relapse? | 1tnqgq2 | 主帖、多个真实评论，至少一支三层评论对话 |
| 6 months clean | 1nigsl9 | 主帖、真实评论及楼主楼中楼回复 |

- https://www.reddit.com/r/problemgambling/comments/1jf6n1r/distraught_relapse_after_1000_days_clean/
- https://www.reddit.com/r/problemgambling/comments/1tnqgq2/whats_usually_happening_right_before_you_relapse/
- https://www.reddit.com/r/problemgambling/comments/1nigsl9

本轮使用 `tests/fixtures/problem-gambling-digests-20261122.json`：**独立重新撰写、标注 QA 的短篇概要及评论主题摘要**，而非原帖原文或真实 Reddit 用户账号。这一组资料只用于验证在开发 D1 里批量入库、评论父子关系、去重和回读，不能称为“完整转载采集成功”。每篇包含公开原帖链接。使用 `site=reddit_digest`，区别于今后的合法完整源数据 `site=reddit`；不修改自动采集站点注册表。

运行路径：`scripts/qa_three_problem_gambling_digests.py` 经 GitHub Actions `.github/workflows/gambling-three-source-qa.yml`。通过专用单次请求文件触发。后续 **只有在独立验证生产脚本的凭据、只读预检查、Time Travel 恢复点、作者和语言映射、幂等性并获本次同步许可后**才允许向生产 D1 同步。若用户希望最终公开的是未经改写的真实全文和评论，须取得相应许可；不能把此 QA 概要说成真实原文。
