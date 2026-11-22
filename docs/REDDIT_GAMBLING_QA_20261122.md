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


## 2026-11-22 本轮真实验收记录
- 三个真实的公开 Reddit 来源链接已核查，原帖有评论及评论回复；未经许可的用户全文 **未复制**。
- 开发预览入库数据是显著标为 `[QA DIGEST]` 的非逐字独立概要和评论主题摘要（不是完整 Reddit 原文，不能冒充用户原话）；`site=reddit_digest`，不会占用未来真实合法采集的 `reddit` 来源 ID。
- [DEV HTTP + D1 完整采集闭环 #44977768483](https://github.com/119shenhao/gambling/actions/runs/44977768483) **Success**。`exclusions → claim → complete → GET topic 回读 → completed 排除` 实际通过；开发库新增三篇、11 条评论（含楼中楼，第二篇含三级结构）。
- DEV 主帖：
  - [复赌记录概要](https://dev-gambling-community.119shenhao.workers.dev/topic/8aea9372-9c44-454a-bdcb-bed14b220675)，主帖 UUID `8aea9372-9c44-454a-bdcb-bed14b220675`，4 条回复。
  - [复赌诱因概要](https://dev-gambling-community.119shenhao.workers.dev/topic/ed6f1bae-05b4-422e-b304-fa8f4dbdd69a)，主帖 UUID `ed6f1bae-05b4-422e-b304-fa8f4dbdd69a`，4 条回复，三级层级。
  - [六个月戒赌记录概要](https://dev-gambling-community.119shenhao.workers.dev/topic/83a733ea-2c19-4894-8893-cb2fe6c2c851)，主帖 UUID `83a733ea-2c19-4894-8893-cb2fe6c2c851`，3 条回复。
- [独立 SQLite/TypeScript 同步回归 #44977916908](https://github.com/119shenhao/gambling/actions/runs/44977916908) **Success**：25/25 CI 测试通过，包括重复执行 SQL 幂等、主帖内容指纹、当前版本语言证明及三级父子层级和匿名系统作者映射。
- [真实生产 D1 只读预检查 #44977832288](https://github.com/119shenhao/gambling/actions/runs/44977832288) **blocked / failure**：专用 GitHub Actions 机密 `GAMBLING_PROD_D1_API_TOKEN` 与仓库变量 `GAMBLING_CLOUDFLARE_ACCOUNT_ID` 未全部提供。作业在任何远程 D1 操作之前停止：**没有生产写入；不能声称生产同步成功**。
- 下一步：由仓库/Cloudflare 管理员通过 GitHub Settings 为赌博项目单独安装生产 D1 Token（Cloudflare Account → D1 → Edit，尽可能限制账号及资源；不使用 Spine Token），并设置账号 ID 变量；再重跑只读 SQL 验证，验证 Time Travel 恢复点，执行批准的单次三篇 QA 摘要正式同步及回读验收，最后确认回执 `marked=examined`、无剩余未同步条目及幂等性。临时 QA 内容应持续明确标注，正式内容应另行获许可。
