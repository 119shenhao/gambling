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
