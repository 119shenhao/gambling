# 戒赌论坛｜采集与内容同步（开发阶段）
日期：2026-11-22。仓库 `119shenhao/gambling`。开发分支 `dev`，正式分支 `main`。

## 已移植的安全边界
- 仅 `https://dev-gambling-community.119shenhao.workers.dev` 能在开发 D1 上启用 HTTP `/api/import/*`、`/api/collect/*`；生产配置的两个开关始终 false 且无 IMPORT_DB 绑定。
- 独立开发 D1 UUID `a92cf620-2a0b-46e1-a0ff-2e0c94218f37`。生产 D1 UUID `7bba9ada-589f-493b-8fcf-60265fc0efac`。从不使用 Spine 的数据库、密钥或业务内容。
- 采集协议：`exclusions → claim（6 小时）→ complete`，失败 `release`。正文指纹、事务原子性、回读、评论 49 条／8 层／150KB 上限保留。导入 API 与采集 API 默认免全局密钥，仅有开发域名、Origin、限流与令牌保护；**这不能代替安全鉴权，必须评估公众滥用风险**。
- 开发专属候选队列表在 `migrations/preview-only/0001_collector_queue.sql`；生产迁移链不包含它。开发预览构建自动执行受门禁控制的队列表迁移。
- 内容同步脚本 `scripts/sync-preview-to-production.mjs` 默认 dry-run；正式写入必须有 `--apply`、精确生产 D1 确认值、生产审查与 Time Travel 恢复点。按 `published` 且无回执筛选，首次携带公开评论和楼中楼；生产作者映射系统 Anonymous；生产已有同指纹跳过，写后核验才记录 `topic_sync_receipts`；有回执后永久不再增量同步。
- 多语言原文证据仅使用当前版本的人工或可靠验证，未知标 `und`，不伪造语言标签。

## 采集器的来源状态与未完成事项
- `scripts/gambling_collect.py` 已准备独立的 GitHub 请求文件协议（`request_id`、`mode`、`sites`、`candidates`、`limit`）及授权完整 JSON 导出入库。请求文件不会包含论坛用户正文或临时认领令牌。
- **目前 `scripts/gambling_sources.json` 的来源列表为空**。不能将 Spine 的六个医学来源当成戒赌来源；未核实合法授权、原帖唯一 ID、页面解析、完整回复校验的戒赌站点不得自动抓取或批量转载。默认的按时采集任务应报告来源未配置，而不是伪造新增。
- 从经过合法授权的来源建立稳定发现/解析器并在独立开发预览完成真实 HTTP / D1 端到端验收之后，再让定时采集进入 collect 模式。
- 生产同步 Workflow 必须先安装专用 GitHub `GAMBLING_PROD_D1_API_TOKEN` 机密及账号变量、做新脚本只读预检查、测试恢复点/幂等/生产回读，再获得生产发布审批。**未通过这些验收不得由 ChatGPT 定时任务触发生产写入。**
- 开发站路由和迁移仅有代码/CI 检查不等于线上 API 已部署；需核实 `GET /api/health` 的 `importEnabled`/`collectEnabled`，以及排除列表和认领释放的真实 HTTP 结果。
- 定时采集与生产同步不可使用同一数据库或复用 Spine GitHub Actions 作业；定时任务也不得把提交成功当成工作流执行成功。

## 2026-11-22 开发采集和同步安全验收（本次）
- [DEV 三篇来源链接摘要测试](https://github.com/119shenhao/gambling/actions/runs/44977768483)：HTTP 真实入库 3 主帖、11 评论、含楼中楼、三级父子关系；`source=reddit_digest` 为 QA 独立摘要，不是获得授权的全文转载。
- [同步 SQLite 功能测试](https://github.com/119shenhao/gambling/actions/runs/44977916908)：25/25 通过，确认重复执行幂等及评论父子关系。不能当作远程 Cloudflare D1 成功。
- [正式数据库只读预检查](https://github.com/119shenhao/gambling/actions/runs/44977832288)：缺少 `GAMBLING_PROD_D1_API_TOKEN` 或 `GAMBLING_CLOUDFLARE_ACCOUNT_ID` 中至少一项，在连接 D1 前失败，生产数据库保持未动。必须设置专用凭据并执行首次只读与受控同步验收；不能借用 Spine Token。
- 3 个 DEV UUID：`8aea9372-9c44-454a-bdcb-bed14b220675`、`ed6f1bae-05b4-422e-b304-fa8f4dbdd69a`、`83a733ea-2c19-4894-8893-cb2fe6c2c851`。进入生产前需要确认内容已清楚标注 QA 摘要，原作者未获转载许可情况下不得抹掉摘要标签。

## 2026-11-22 首次真实生产同步已通过、定时同步已重新接通
- 用户明确要求继续自动补齐生产同步，避免手动设置 token。此前失败的赌博仓库工作流需要单独 Secret `GAMBLING_PROD_D1_API_TOKEN` 及账号 ID；**当前已采用经过验证的另一条安全通道，无需复制任何密钥**。
- [首次生产试同步 #44978277965](https://github.com/119shenhao/identity-center/actions/runs/44978277965) PASS：从本论坛独立 DEV D1 到独立 PROD D1 成功同步 3 篇明确标示 `[QA DIGEST]` 的 Reddit 讨论独立摘要、11 条评论与楼中楼，新增 3 个源端回执；读回全部回复、语言、作者映射、层级，第二次 dry-run `examined=0`。生产 Time Travel 恢复点已事先校验并安全记录。
- 认证中心仓库 `119shenhao/identity-center/main` 已保存经验证的 D1 访问令牌（之前为戒赌论坛生产 D1 做过初始化，当前仍有效），其 `.github/workflows/gambling-content-sync-protected.yml` 是此论坛专属内容同步执行器。令牌仅在该仓库 **GitHub Actions production** 环境使用，不写入或复制到赌博仓库，不与 Spine 使用相同 Github Repo Secret，D1 UUID 完全隔离。
- 通过在 `identity-center/main/.github/gambling-content-sync-request.json` 提交唯一 request_id、`mode=sync`，触发经批准固定 SHA 的同步脚本：先核对目标 D1、独立源码 CI/SQL 回归、只读预检查及 Time Travel 恢复点，然后按发布与一次性回执规则执行；已同步主帖永远跳过，绝不补传后续评论；完成再回读 `examined=0`。无 API 写入口或结构迁移。
- ChatGPT 固定任务「戒赌论坛同步生产帖子」已更新为采用认证中心的受保护工作流，频率仍每12小时。**不要再触发赌博仓库原先缺少 secret 的 `gambling-sync-posts.yml`**；将来要迁移到独立新令牌，需要另行验收。用户不需要通过聊天提供任何密钥。
- 采集定时任务每6小时仍处于启用状态，但 `scripts/gambling_sources.json` 仍无合法授权/稳定解析的真实戒赌站点，不得把已完成的 3 篇 QA 独立摘要当作自动复制 Reddit 原帖全文。后续只有明确获授权的来源才能运行真正定时采集。
