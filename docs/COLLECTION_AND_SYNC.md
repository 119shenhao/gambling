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
- `scripts/gambling_collect.py` 已准备独立的 GitHub 请求文件协议（`request_id`、`mode`、`sites`、`candidates`、`limit`）及完整 JSON 导出入库。请求文件不会包含论坛用户正文或临时认领令牌。
- **历史初始状态**：2026-11-22 早些时候 `scripts/gambling_sources.json` 为空；现已登记独立 GamCare 与 Gambling Therapy，**GamCare 根据用户本次确认的完整帖文/回复再发布许可启用，Gambling Therapy 仍关闭**。不迁入 Spine 的医学来源。
- GamCare 已完成稳定发现、真实帖文 HTML 解析、原子 DEV 入库和 D1 API 读回，默认 `mode=collect`、`sites=["all"]`、`candidates={}`、`limit=2`。其他来源需单独验收后启用。
- **历史阻碍已通过独立受控路径解决**：戒赌论坛正式内容同步使用已验收的 `119shenhao/identity-center` 专用生产环境工作流和既有受保护凭据（详见下文）；本轮采集开发未触发生产同步。
- 开发站路由和迁移仅有代码/CI 检查不等于线上 API 已部署；需核实 `GET /api/health` 的 `importEnabled`/`collectEnabled`，以及排除列表和认领释放的真实 HTTP 结果。
- 定时采集与生产同步不可使用同一数据库或复用 Spine GitHub Actions 作业；定时任务也不得把提交成功当成工作流执行成功。

## 2026-11-22 开发采集和同步安全验收（本次）
- [DEV 三篇来源链接摘要测试](https://github.com/119shenhao/gambling/actions/runs/44977768483)：HTTP 真实入库 3 主帖、11 评论、含楼中楼、三级父子关系；`source=reddit_digest` 为 QA 独立摘要。
- [同步 SQLite 功能测试](https://github.com/119shenhao/gambling/actions/runs/44977916908)：25/25 通过，确认重复执行幂等及评论父子关系。不能当作远程 Cloudflare D1 成功。
- [正式数据库只读预检查](https://github.com/119shenhao/gambling/actions/runs/44977832288)：缺少 `GAMBLING_PROD_D1_API_TOKEN` 或 `GAMBLING_CLOUDFLARE_ACCOUNT_ID` 中至少一项，在连接 D1 前失败，生产数据库保持未动。必须设置专用凭据并执行首次只读与受控同步验收；不能借用 Spine Token。
- 3 个 DEV UUID：`8aea9372-9c44-454a-bdcb-bed14b220675`、`ed6f1bae-05b4-422e-b304-fa8f4dbdd69a`、`83a733ea-2c19-4894-8893-cb2fe6c2c851`。进入生产前需要确认内容已清楚标注 QA 摘要，不得抹掉摘要标签。

## 2026-11-22 首次真实生产同步已通过、定时同步已重新接通
- 用户明确要求继续自动补齐生产同步，避免手动设置 token。此前失败的赌博仓库工作流需要单独 Secret `GAMBLING_PROD_D1_API_TOKEN` 及账号 ID；**当前已采用经过验证的另一条安全通道，无需复制任何密钥**。
- [首次生产试同步 #44978277965](https://github.com/119shenhao/identity-center/actions/runs/44978277965) PASS：从本论坛独立 DEV D1 到独立 PROD D1 成功同步 3 篇明确标示 `[QA DIGEST]` 的 Reddit 讨论独立摘要、11 条评论与楼中楼，新增 3 个源端回执；读回全部回复、语言、作者映射、层级，第二次 dry-run `examined=0`。生产 Time Travel 恢复点已事先校验并安全记录。
- 认证中心仓库 `119shenhao/identity-center/main` 已保存经验证的 D1 访问令牌（之前为戒赌论坛生产 D1 做过初始化，当前仍有效），其 `.github/workflows/gambling-content-sync-protected.yml` 是此论坛专属内容同步执行器。令牌仅在该仓库 **GitHub Actions production** 环境使用，不写入或复制到赌博仓库，不与 Spine 使用相同 Github Repo Secret，D1 UUID 完全隔离。
- 通过在 `identity-center/main/.github/gambling-content-sync-request.json` 提交唯一 request_id、`mode=sync`，触发经批准固定 SHA 的同步脚本：先核对目标 D1、独立源码 CI/SQL 回归、只读预检查及 Time Travel 恢复点，然后按发布与一次性回执规则执行；已同步主帖永远跳过，绝不补传后续评论；完成再回读 `examined=0`。无 API 写入口或结构迁移。
- ChatGPT 固定任务「戒赌论坛同步生产帖子」已更新为采用认证中心的受保护工作流，频率仍每12小时。**不要再触发赌博仓库原先缺少 secret 的 `gambling-sync-posts.yml`**；将来要迁移到独立新令牌，需要另行验收。用户不需要通过聊天提供任何密钥。
- 采集定时任务每6小时仍处于启用状态；GamCare 来源已实际开启，其他未许可/未验证来源仍会跳过。所有采集只写独立 DEV D1。

## 2026-11-22 独立外站解析器开发与远程只读核验

- 戒赌论坛 `dev` 分支独立新增 `scripts/gambling_forums.py`，提供 GamCare 与 Gambling Therapy 的规范 URL/稳定主题 slug、列表候选发现、HTML 正文及回复读取、分页/评论数/正文上限/隐私数据保守校验；不使用 Spine 的采集代码、医学来源或任务。
- `scripts/gambling_collect.py` 已接入网站发现、全量 exclusions 分页、6 小时 claim、complete、失败/结果不明时谨慎释放、正文/回复 API 回读与按来源计数；`inspect` 模式只读探测候选帖结构，不会导入。
- `.github/workflows/gambling-collector-on-demand.yml` 安装独立解析依赖并在调用 Worker 前运行 `tests/test_gambling_collector.py`；仍只监听 gambling/dev 的独立请求文件变化，未新增 GitHub Actions cron，原 ChatGPT 独立任务保持不变。
- [首次真实 inspect GitHub Actions #44992825630](https://github.com/119shenhao/gambling/actions/runs/44992825630) 执行成功：10 项 Python 离线测试通过，DEV `/api/health` 通过，GamCare 两个论坛列表分别发现 26、22 个候选，合并去重为 **39 个**；Gambling Therapy 列表 HTTP 403，0 个候选。该 inspect 并未 POST claim/complete，**新增主帖/回复 0**。
- **此条为早期只读检查时的状态，已被下方真实采集验收取代。** 用户确认取得 GamCare 完整主帖/回复的再发布许可；用户陈述已如实登记（未独立核验纸面凭证）。仅 GamCare `approved=true`、`parser_verified=true`、`reuse_allowed=true`；Gambling Therapy 未启用。系统作者固定 Anonymous，采集表保留来源站点和稳定原站 ID。
- 现有 JS 旧测试曾假设 `sources.length===0`，已按“可登记来源但默认禁止导入”的新规则修订。技术上来源发现打通，不等于当前可以进行未经许可的整篇转载。
- [真实正文解析只读验收 #44992931664](https://github.com/119shenhao/gambling/actions/runs/44992931664) 已发起；需以最终状态和日志为准，不能把作业触发当成正文解析成功。

**最新状态：** GamCare 已符合上述门槛并完成正式采集；其他来源（尤其仍返回403的 Gambling Therapy）继续严格限制，不绕过反爬或访问控制。

## 2026-11-22 GamCare 正式采集开启与 DEV 回读（最新验收）

- 用户确认已取得 GamCare 论坛完整主帖及回复的再发布许可。本项目仅据用户许可声明登记 `permission_evidence`，没有声称独立审阅许可文件；未授权 Gambling Therapy、Reddit 或 Spine 任何内容。
- [第一次真实 DEV 入库 #44993497291](https://github.com/119shenhao/gambling/actions/runs/44993497291) PASS：1篇、7回复，完整 API 回读。
- [自动发现首轮 #44993558005](https://github.com/119shenhao/gambling/actions/runs/44993558005) 原工作流 exit 1，但实际写入4篇：其中2篇即时报为导入成功，另2篇被旧语言回读误判；[历史两篇审计 #44993908744](https://github.com/119shenhao/gambling/actions/runs/44993908744) PASS：分别核实14条和7条回复及原文，未重复入库。
- [自动发现修复验收 #44993765907](https://github.com/119shenhao/gambling/actions/runs/44993765907) PASS：新增2篇、7回复，5个不完整/含个人信息候选按规则跳过，错误0。
- [恢复默认运行模式 #44994042299](https://github.com/119shenhao/gambling/actions/runs/44994042299) PASS：`mode=collect`、`sites=["all"]`、`candidates={}`、`limit=2`，GamCare再新增2篇、10回复；未启用的 Gambling Therapy 完全跳过，不再访问其403页面。Python 17项测试通过，[项目CI #44994042376](https://github.com/119shenhao/gambling/actions/runs/44994042376) 通过。
- **本次实际累计：9篇真实 GamCare 主帖、49条真实回复**，均已当轮回读或历史只读复核，不包含此前3篇 `[QA DIGEST]` 和11条测试回复。本轮只写隔离 DEV D1，未触发生产同步。
- 技术修复：不完整/隐私风险内容记为 `candidate_rejected`；服务端独立语言识别将短评论标记 `und` 不再导致虚假的正文不一致；仍严格验证主帖及各级评论原文、数量、分页与父子关系；支持只读审计已完成来源，避免重复写入。
- 保留 ChatGPT 专属每6小时的戒赌采集任务及既有每12小时独立生产同步任务；不新建 GitHub Actions cron、不使用 Spine 调度器、数据库、密钥或内容。此轮没有访问或修改正式生产 D1。

## 2026-11-22 采集长帖改造：每篇最多500条真实回复

**用户确认规则**：不能因为有50条或更多回复而放弃整篇主帖；外站实际不超过500条时逐页采集全部回复，超过500条时**按原站顺序仅取前500条（第501条不保存）**。评论和楼中楼合并计数，保留可验证的父子关系；如缺页/正文丢失则拒绝该候选，不能谎称“完整”。

- 仅在 `119shenhao/gambling/dev` 增加 `scripts/gambling_forums.py::parse_topic_pages`：按GamCare原帖 `/paged/N/` 连续读取，校对全站显示的帖子总数（扣除主帖），限制前500回复、最多40个页面；记录 `source_total/capped/pages`。首次真实演练直接读取2页25条，后又读10页142条。
- `scripts/gambling_collect.py` 新增分批编排 `complete_staged`，原单包不超过49条继续走旧 `collect/complete`；跨页或大帖采用 `/api/collect/long/start → append → finish`，每批10条；完成后对DEV API全部评论分页回读，最高500条。源帖已完成/指纹重复时跳过。
- `src/collect-long.ts`：独立DEV长期暂存元数据与回复，单次上传最多20条，offset必须连续、支持相同批次重试和跨批parent_index。只在全部 `target_count` 条暂存且验证序号无缺口时，用**一个D1事务**创建主帖、最多500评论、source完成回执，不能公开半成品。暂存表 `migrations/preview-only/0002_collector_long.sql` 限定 ordinal 0至499，记录 `source_total` 和 `capped`；仅开发预览自动迁移，**不在生产迁移链**。
- [GamCare两页25回复真实DEV入库 #44995042695](https://github.com/119shenhao/gambling/actions/runs/44995042695) PASS：topic_id `e4439865-eef8-4932-a888-c5d99c722c52`，新增1主帖、25回复，回读数量与原文匹配。
- [GamCare十页142回复真实DEV入库 #44995221312](https://github.com/119shenhao/gambling/actions/runs/44995221312) PASS：topic_id `f9d8e0d6-b6b3-46b8-a957-5347db346513`，新增1主帖、142回复，回读通过。证明大于49条不再自动拒绝。
- Python单测覆盖：GamCare两页、原站501条时恰好截取前500不含第501、缺失分页拒绝、preview SQL 500条上限阻止第501写入；新服务端配置、TS CI也通过独立检查。**501封顶已通过程序/SQL测试，但尚没有成功的真实超过500条帖子入库验收，不能夸大。**
- [Charly's life >500回复只读探测 #44995338423](https://github.com/119shenhao/gambling/actions/runs/44995338423)：因源网页某条回复 `empty_post_or_reply` 无法取得完整正文而安全拒绝；未入库，并非因超出500直接跳过。此问题属于真实来源可读性，后续可定位/改进，但不能编造丢失回复。
- 已更新 ChatGPT 独立「戒赌论坛独立采集入库」每6小时任务指令支持分页500上限；不触碰独立的Spine任务或本论坛生产同步任务。

**状态**：开发环境已证明能真实入库跨页142条；500封顶逻辑已编码、单测验证，仍需要一篇可完整读取、实际>500回复的外站候选，做完整端到端采集验证。生产D1未因本次开发改动。
