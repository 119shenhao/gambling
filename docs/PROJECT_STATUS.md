# 项目状态 — Gambling Community

- 2026-11-21 新建空仓库 `119shenhao/gambling`，main 仅有项目入口，dev 进行源码移植。
- 采用 `spine-community/main` 通用代码，并改造产品命名、分类、SEO 域名、统一身份登录新用户映射。
- 所有原站 D1/R2、Google OAuth、采集/同步生产任务均未迁入；新站仅能本地使用独立 D1。公开站点及生产 OAuth 尚未配置。
- 尚需：CI 与本地 D1 验收、领域旧字段全面清理、隐私与社区规则、完整多语言校对、创建预览 D1、注册 Identity Center 开发客户端、真实 Google SSO 双论坛场景、内容安全与生产部署审批。
- 本阶段复制代码并非宣称新站已正式发布。

## 2026-11-21 初次源码移植验收

- 开发分支提交：`a2b33624bc74813c280bddeccff8ac3a3fc10d7a`，共 80 个文件。
- [GitHub Actions 首轮 CI #44881408456](https://github.com/119shenhao/gambling/actions/runs/44881408456)：**成功**。`npm ci`、`npm run verify`（TypeScript + 产品隔离/品牌自动检查）、`npm run db:local`（全部独立本地 D1 迁移）、`npm run build`（前端版本化构建）全部完成。
- 此结果证明源码可以在 CI 中通过检查与本地迁移，**不证明浏览器端所有业务交互、真实 Google/Identity Center 登录、Cloudflare 预览或生产已经可用**。
- 不复制原站已验证的 Google 域名证明页面、Cloudflare D1/R2 绑定、远端采集/同步 Actions；原数据没有导入。
- 技术债：仍存在源项目兼容字段（如 `body_part` / `symptom_duration_days`），其业务 UI 已初步隐藏/简化；应逐步清理并完成真实端到端回归。源项目大规模医疗业务测试不能直接当作新站验收。

## Cloudflare 资源已创建（用户确认；待 UUID 回读）

用户 2026-11-21 表示已经创建 Worker `gambling-community`、开发/生产 D1 `gambling-community-dev` / `gambling-community-prod` 和开发/生产 R2 `gambling-community-public-dev` / `gambling-community-public-prod`。

- dev 的 `wrangler.jsonc` 已新增正确的 Preview / Production R2 绑定和分环境 `APP_ENV`，不包含任何原 Spine 的资源 ID。
- 暂**没有** Cloudflare 控制台 API 授权，不能独立核实新 D1 UUID、Worker 生产/预览构建状态或 R2 存在情况。资源创建按用户确认记载，不能宣称已经远程绑定或迁移。
- 新 D1 的 UUID 仍必须取自 Cloudflare D1 详情页面；获得两个真实 UUID 后，单独绑定两套数据库并在开发预览执行版本化迁移。**开发验证前不做生产迁移**。
- R2 只是绑定到环境；公开 JSON 读取/回填仍关闭，待开发端流程和 CDN 域名验收后才开启。
- 详细操作及避免手工运行的开发迁移流程见 [CLOUDFLARE_SETUP.md](CLOUDFLARE_SETUP.md)。

- 2026-11-21 已准备预览 D1 自动迁移安全门禁 `scripts/preview-migrate.mjs`：仅 Cloudflare 的 dev Preview，核对 D1 UUID、名称及独立绑定后执行；UUID 尚未提供时不运行远程 SQL。生产迁移未授权。

## 2026-11-21 D1 真实 ID 绑定

用户提供的 Cloudflare D1 控制台截图明确显示：

- 开发 D1：`gambling-community-dev`，UUID `a92cf620-2a0b-46e1-a0ff-2e0c94218f37`。
- 生产 D1：`gambling-community-prod`，UUID `7bba9ada-589f-493b-8fcf-60265fc0efac`。

两套 UUID 均已加入 `dev/wrangler.jsonc` 的对应 Preview 与 Production 分环境绑定。新建 `wrangler.preview-migrations.jsonc` 仅指向开发 D1 的 UUID；`scripts/preview-migrate.mjs` 以两个已确认的 UUID 和环境分支为白名单安全验证。

**注意**：只完成源码配置/提交，并非已连接 Cloudflare API 实际迁移。开发远程迁移将在合规 Cloudflare dev Preview Build 中运行，待查看实际部署日志和数据库状态；生产库始终不执行迁移。

## 2026-11-21 D1 配置提交后验证

- 开发配置提交 [`99fbc46aae68258c05c47feefa533c8ed47487d5`](https://github.com/119shenhao/gambling/commit/99fbc46aae68258c05c47feefa533c8ed47487d5)，将用户截图确认的独立开发/生产 D1 UUID 分别绑定，自动迁移专用配置只指向开发库。
- [GitHub Actions #44882745486](https://github.com/119shenhao/gambling/actions/runs/44882745486)：**通过**。包含 `npm ci`、`npm run verify`、`npm run db:local` 与 `npm run build`。
- 该 GitHub Actions 不持有 Cloudflare 远端数据库写入权限，`scripts/preview-migrate.mjs` 在非 Cloudflare dev Preview 构建中安全跳过；CI 通过**不能当成远端 D1 已迁移**。
- 云端 Worker Preview URL、Cloudflare Build 实际日志、D1 表数量和 `/api/health` 仍未验证。继续开发前应提供该 Worker 的实际 Preview URL 或 Cloudflare Build 截图；之后再判断远程迁移、Worker 与真实身份联调的下一步。

## 2026-11-21 GitHub 仓库更名

- 用户已将本项目仓库更正为 **`119shenhao/gambling`**；GitHub Connector 检查新旧 URL 均解析到仓库 ID `1466297378`。不是另建仓库，分支与提交历史保持不变。
- 本项目文档、GitHub Actions 历史链接与固定入口均更新为新仓库地址。
- Cloudflare Worker `gambling-community`、两套 D1 和 R2 名称及 UUID 均保持原样，不能为了仓库更名重建。
- Cloudflare Git 构建集成可能需核对仓库连接是否同步更新；仅仓库改名**不等于**已经验证 Cloudflare Preview 部署或远程迁移。

## 2026-11-21 全仓库移植残留审计

完整检查 `dev` 下全部 83 个文件，确认 GitHub 旧仓库拼写已移除（测试中禁止回归的正则除外）；额外发现并修复了旧站的后台预览确认值、网页侧栏品牌、公开 JSON CDN 备用主机、Projection 默认来源域名、失效 Header 名、公开分享站点名称、下载文件名、PV Cookie/哈希前缀及界面本地储存键。

- `PUBLIC_CONTENT_ORIGIN` 仅在确认**实际**新论坛 Preview URL 后由开发环境配置；新的 `gambling-data-dev.nbn369.com` / `gambling-data.nbn369.com` 均为规划，不代表已建立 DNS/CDN。公开 JSON 功能继续关闭。
- 现有 `public/i18n.js` 的旧词库基础字典包含少量脊椎/医疗专用旧字符串，实际主要页面采用后置 `gamblingCopy` 覆盖；在公开发布前仍需完成全语言键覆盖核对和专业人工校对，不得宣称国际化完全验收。
- 已添加残留回归自动测试，并验证前后端 `gambling-community-dev` 的危险操作确认值保持一致。

## 下一阶段：统一身份认证准备

已在 `dev/wrangler.jsonc` 中分别声明公开的身份签发者与独立 Client ID：开发 `gambling-community-dev` 使用开发 Identity Center，正式 `gambling-community-prod` 使用生产 Identity Center。两套登录均保持 `IDENTITY_LOGIN_ENABLED=false`，不包含密钥或猜测的回调 URI。**这不是注册完成，也不是登录已可用**。需要先获得 Cloudflare 实际 Preview URL，确认新项目自动构建的成功日志，再注册开发 Identity Center Client，受控配置 Secret、开启登录并进行真人验证。不得复用 Spine 已登记的客户端及密钥。

## 2026-11-21 开发与生产 URL 确认

用户提供实际开发入口 `https://dev-gambling-community.119shenhao.workers.dev/`、生产入口 `https://gambling.nbn369.com/`。已写入 `wrangler.jsonc` 的独立 Identity Center 精确回调准备值，登录仍关闭，生产尚未部署。新增 GitHub Actions 在线只读开发站 Smoke，用于检查首页、`/api/health` 的 Preview+D1 Ready、robots 禁索引及旧 Google 登录禁用。等待实际运行结果，不得用 GitHub CI 本地 D1 成功冒充远程已迁移。

## 2026-11-21 开发站在线 Smoke 与 Identity Center 客户端登记

- 用户确认开发网址 `https://dev-gambling-community.119shenhao.workers.dev/`、生产网址 `https://gambling.nbn369.com/`，开发与生产精确回调 URI 已写入 `dev/wrangler.jsonc`，均**未启用登录**。
- [在线 Smoke #44883988827](https://github.com/119shenhao/gambling/actions/runs/44883988827) 由 GitHub Actions Runner 对开发站真实 HTTP 访问：`/api/health` HTTP 200、`environment=preview`、`status=ok`、`databaseConfigured=true`、`databaseReady=true`；首页包含 Problem Gambling、robots.txt 为 `Disallow: /`、旧直连 Google 登录端点为 410；这些都**线上通过**。
- [本地 CI #44883988728](https://github.com/119shenhao/gambling/actions/runs/44883988728) 成功，含 TypeScript、独立本地 D1 迁移和构建。
- [Identity Center DEV 客户端登记 #44884259846](https://github.com/119shenhao/identity-center/actions/runs/44884259846) 成功：`identity-center-dev` 中创建/校验 `gambling-community-dev`（web_confidential、status=disabled），唯一回调 `https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback`；没有创建 Secret、没有开启认证，也没有写入认证中心生产 D1。
- 参考已验收 Spine 的跨 Worker OAuth 经验，为新论坛补上 `global_fetch_strictly_public` Worker 兼容选项（仅在 dev 源码上改动）。
- **待办**：为客户端生成独立随机 Secret，原文只保存在新的开发 Worker Cloudflare Secret，Identity Center 开发库只保存摘要；验证匹配并启用开发客户端，最后才打开论坛 `IDENTITY_LOGIN_ENABLED`，检查真实 Google 登录与会话。禁止直接使用 Spine Client/Secret。开发用户真实验收之前不变更生产登录、生产 D1 或正式站发布。

## 2026-11-21 One-time DEV OAuth Secret bootstrap 代码准备

- 新增 `scripts/provision-dev-identity.mjs` 和仅指向 Identity Center DEV D1 的 `wrangler.identity-dev-provision.jsonc`。脚本只允许在 `WORKERS_CI=1` 且分支 `dev`、严格核对 Worker/两套环境 D1 ID/Client ID/Callback 并确认中心客户端 Disabled 后执行。
- 用开发 Cloudflare Preview Worker Secret 命令安全保存随机 48 字节服务端凭据；不在 Git、聊天、日志或 D1 存储明文；在两个 DEV D1 仅保存 SHA-256 Base64URL 摘要，并在身份中心中注册一致摘要。**不启用客户端或登录，也不修改生产。**
- 本提交仅准备脚本并加静态/语法测试，尚未挂到 Cloudflare 构建；下一步先看 CI 通过，再短暂启用一次性开发构建入口，取得真实 Cloudflare 回执，成功后移除一次性调用。若 Cloudflare build 权限不足则暂停，不索取明文 Secret。

## 2026-11-21 DEV SSO Secret 与客户端激活验证

- DEV 论坛 Cloudflare Preview Build 安全运行一次性 Secret bootstrap。独立随机 Secret 原文仅写入预览 Worker，两个开发 D1 只存 SHA-256 Base64URL 摘要；[身份中心只读验收 #44885090134](https://github.com/119shenhao/identity-center/actions/runs/44885090134) 检查了唯一有效摘要和禁用状态，结果成功。
- 已从 `scripts/prepare-build.mjs` 移除一次性 bootstrap 的自动调用，后续普通构建不会再次生成或轮换 Secret；保留脚本但不自动执行。
- [Identity Center DEV 客户端激活 #44885210412](https://github.com/119shenhao/identity-center/actions/runs/44885210412) 成功：`gambling-community-dev` 已启用，有效摘要唯一、回调唯一且精确匹配。未动生产认证中心/论坛数据。
- 将 `dev/wrangler.jsonc → previews.vars.IDENTITY_LOGIN_ENABLED` 开启，仅开发 Preview，正式站仍关闭。通过新工作流 `dev-oauth-smoke.yml` 在线验证 `/api/me`、授权码登录重定向和 PKCE、无状态回调拒绝、旧 Google 直连 410；**真人 Google 回跳尚待用户验收**。

## 2026-11-21 DEV OAuth 线上预登录自动验收通过

- [Gambling DEV OAuth pre-login smoke #44885314371](https://github.com/119shenhao/gambling/actions/runs/44885314371)：**通过**。真实访问开发站 `/api/me` 返回 `identityConfigured=true`；`/api/auth/identity` 返回 302 到 Identity Center DEV 的 `/oauth/authorize`；`client_id=gambling-community-dev`、精确回调、PKCE S256、state、nonce 全部正确；旧直连 Google 端点返回 410；未携带浏览器 state 的回调返回 401。
- [最终开发 CI #44885336995](https://github.com/119shenhao/gambling/actions/runs/44885336995) 通过，含 TypeScript、本地数据库迁移和构建；[开发站只读健康 #44885337025](https://github.com/119shenhao/gambling/actions/runs/44885337025) 成功。
- 认证中心开发客户端单独 Secret 安装及 SHA-256 摘要校验成功 [#44885090134](https://github.com/119shenhao/identity-center/actions/runs/44885090134)；应用启用成功 [#44885210412](https://github.com/119shenhao/identity-center/actions/runs/44885210412)。论坛开发登录开关 true，生产 false。
- **剩余用户验收**：浏览器从 `https://dev-gambling-community.119shenhao.workers.dev/` 主动点击 Google 登录，观察是否回到论坛且显示已登录；在 Identity Center DEV 会话管理检查 `gambling-community-dev` 应用会话；测试退出、重新登录。该真人 Google OAuth 完整往返目前未自动执行、不能标记为通过。
- 认证中心生产与论坛生产的应用客户端、数据库、域名没有切换；Azure Translator 和 R2 公开缓存未启用。

## 2026-11-21 跳过 Identity Center 的提供商选择页（仅开发）

用户实际完成 Google 登录，但要求戒赌社区点击登录后不再显示 Identity Center 的中间选择页。认证中心 DEV 已支持 `gambling-community-dev` 专用、严格约束客户端+Issuer+回调的 `provider_hint=google`；保留中心 SSO 复用、PKCE、Nonce、State、一次性授权码及后端验签和会话处理。认证中心线上真实跳转 [#44886399265](https://github.com/119shenhao/identity-center/actions/runs/44886399265) 成功，未提示时原选择页不变。

本次新论坛 DEV `src/auth.ts` 仅在精确开发配置下传 `provider_hint=google`，不直接访问 Google OAuth，也不修改正式站。`dev-oauth-smoke.yml` 更新为验证论坛 → 身份中心 → Google 两次 HTTP 302 及证明 Cookie，全程不跟随到 Google 页面，不记录敏感查询参数。**仍需用户实际浏览器验收**。

## 2026-11-21 Google 直达自动验收已通过

- 开发中心 [在线 #44886399265](https://github.com/119shenhao/identity-center/actions/runs/44886399265)：`gambling-community-dev` 配合 `provider_hint=google`、固定回调时直接 302 到 Google，上游浏览器事务 Cookie 安全设置；未传参数的原选择页仍可用。
- 戒赌论坛 [完整在线 #44886496949](https://github.com/119shenhao/gambling/actions/runs/44886496949)：`/api/me` 的 `identityConfigured=true`，完整两段跳转 **论坛 → Identity Center DEV（不展示 HTML 页面）→ Google OAuth** 成功；回调缺少 state 拒绝和直连 Google 410 仍通过。
- [完整 CI #44886496923](https://github.com/119shenhao/gambling/actions/runs/44886496923) 通过（TypeScript、本地 D1 和构建）；仅 DEV 分支部署。正式站域名及 Identity Center 生产端未修改。
- 用户修改前实际完成 Google 登录；修改后需要用户再次从论坛点击 Google 登录，确认不会再出现中间选择页、成功返回论坛。若登录期间短暂显示 Identity Center URL 属于正常的 HTTP 302 中转，不应出现中间 HTML 页面。

## 2026-11-21 Azure Translator 接入准备与开发 CI

- 戒赌论坛 Azure 接口、D1 同版本译文缓存、语言识别和管理员额度页面来自既有脊椎论坛成熟方案，本次开发只接入独立 DEV 配置和安全预算。
- [开发提交 416f1bde3dd9f7c27ab6ea9b05cf5063a24e483b](https://github.com/119shenhao/gambling/commit/416f1bde3dd9f7c27ab6ea9b05cf5063a24e483b)：DEV Worker 的 `TRANSLATION_ENABLED=true`、`TRANSLATOR_REGION=eastus`、`TRANSLATOR_F0_VERIFIED_AT=2026-11-09T06:14:50Z`，每日 5,000、每月 50,000 字符；正式 Worker 仍关闭。此日期源自共享 Azure 资源在 Spine DEV 的既有 F0 核验配置，后续过期必须重新核验，不得伪造新的确认时间。
- 翻译硬上限 `AZURE_SITE_MAX_MONTHLY=50000`，管理员不能上调超过该值，月配额与滚动31天预算沿用原子 D1 预约机制。Spine 代码可上限 1.9m/月，两站组合最大 1.95m/月，只针对两站有效，不能当作 Azure 账户的实时计量或支出保证。
- 新增管理员翻译启停按钮、仅在开发且已验证 Azure Secret/F0 时才允许打开 D1 `settings.translation_enabled`；修正 Azure provider 状态返回 `translationEnabled`，避免按钮显示和实际 D1 状态不一致。
- [线上健康和 SSO 回归 #44888634541 / #44888634514](https://github.com/119shenhao/gambling/actions/runs/44888634541) 通过；[代码 CI #44888634510](https://github.com/119shenhao/gambling/actions/runs/44888634510) 通过。上述通过 **不等于** Azure 实际翻译成功。
- **尚未完成**：为新论坛 DEV 命名 Preview Worker 注入现有 F0 资源的 `TRANSLATOR_KEY` Secret，检查云端配置状态，确认新论坛管理权限、启用 D1 开关并进行一条测试贴英⇄中翻译、同版本缓存复用和真实 Azure 用量对账。新旧 Worker Secrets 不能通过 GitHub 读取或自动导出，用户不用将任何密钥发给 ChatGPT。
- R2 公开 JSON 仍禁用，生产 D1、生产 Worker 翻译开关均未更改。

## 2026-11-21 DEV Azure Key 验证与临时联调

- [线上 DEV Worker 密钥存在性检查 #44889584465](https://github.com/119shenhao/gambling/actions/runs/44889584465) 通过：`translationSetup.keyConfigured=true`、地区/旧 F0 核验/翻译结构正常；开发 D1 翻译开关仍关闭。
- 开发与生产使用同一个 Azure Key，但两套 D1 的预算不共享。因此将戒赌论坛每套环境月度硬上限降低到25,000；开发预设10,000、生产预设25,000；两者管理员最多分别提升到25,000。即使加上 Spine 的最多1.9m，理论上还留50k余量，**不包括 Spine Preview 或其他 Azure 消费者，必须由 Azure 账户真实用量总控**。
- 增加仅开发有效的一次性真实 Azure 翻译诊断 `POST /api/dev/azure-smoke`，只发送固定的英中两句，不涉及用户内容，在 D1 唯一键上防重并记录预算消耗；成功后删除测试入口。诊断尚未运行成功前不得声称 Key 已经过 Azure 验证。
- 生产环境只预置 `TRANSLATOR_REGION=eastus`、F0 既有验证日期、预算变量，`TRANSLATION_ENABLED=false` 不变，不更改生产 D1 或发布尚未验收的新站。


## 2026-11-21 · 每次主动 Google 登录都提供账号选择（仅 DEV）

按用户新要求，仅保留“使用 Google 登录”一个按钮；点击后要求 Google 显示可选旧账号或使用其他账号的界面，不能默默复用 Identity Center 中已有的 SSO 身份。DEV 的 `src/auth.ts` 在既有 PKCE/state/nonce 和精确回调上携带 `provider_hint=google&prompt=select_account`；注册/启用的 Google 网站均使用相同方式，正式论坛的 `IDENTITY_LOGIN_ENABLED=false` 保持不变。认证中心 DEV 配合新授权行为：已有 Center Cookie 也直接转 Google（上游 `prompt=select_account`）。不恢复旧的直接 Google OAuth 登录路由，不混用 Spine 用户或数据库，不改帖子/角色。生产须另外批准并验收。

## 2026-11-21 Cloudflare Preview Secret 丢失问题已定位（待用户重新绑定）

- 第一次 [DEV 真实 Azure 自动测试 #44889928443](https://github.com/119shenhao/gambling/actions/runs/44889928443) 返回 HTTP 503；D1 诊断 `azure_dev_smoke_20261121=not_started`、预算 0，**没有调用 Azure 产生字符费用**。
- [DEV Secret 验证 #44889584465](https://github.com/119shenhao/gambling/actions/runs/44889584465) 曾显示 `keyConfigured=true`；随后多个 DEV Cloudflare Preview 构建后，新版本返回 `keyConfigured=false`、`azureConfigurationReady=false`。[只读诊断日志 #44890037912](https://github.com/119shenhao/gambling/actions/runs/44890037912) 留存了对比。这说明 DEV 命名 Preview 的运行时已失去 Secret 绑定，**不是 Azure Key 已被证明无效**。
- Cloudflare 资料说明 Preview Base Secret 变更不会同步到已创建的命名 Preview；确实也存在历史上 Preview 重新部署后丢失 Secret 的已修复 SDK 缺陷（[Cloudflare 问题 #15942](https://github.com/cloudflare/workers-sdk/issues/15942)）。当前仓库 package-lock Wrangler 是 `4.158.0`，晚于修复版，因此不能仅据此认定遇到了同一个老 bug。需在最终代码部署后将 `TRANSLATOR_KEY` **绑定到已存在的 `dev` 命名 Preview 的最新部署**，不要只填写 Preview Base。Secret 明文不可读取或从 Prod 自动复制。
- 现在把 DEV 一次性实测路径改为：只有同一 Secret 完成英→中和中→英两次真实成功，才通过一个 D1 batch 设置 active provider Azure、每日5000、每月10000与 `settings.translation_enabled=true`，失败保持关闭。随后回归验证预算和页面译文缓存；生产开关保持关闭，待论坛正式版验收。

## 2026-11-21 Secret 持久化要求与自动监控

用户再次在 `dev` 命名 Preview 保存 Azure Key；重新运行开发站在线检查已确认 `translationSetup.keyConfigured=true`（[重新检查](https://github.com/119shenhao/gambling/actions/runs/44890627081)）。此轮新增发布后 `dev` Secret 持久化检查，并把不得覆盖 Cloudflare Secret/Variables/D1/R2 写入 `docs/CLOUDFLARE_SETUP.md`；生产仍不开放自动翻译。普通构建禁止对 Secret 执行 put/delete。发布监测会因真实在线键缺失失败，不会尝试恢复/暴露 Key。

## 2026-11-21 Azure 双语验证成功、启用 DEV 数据库翻译、拆除临时接口

- [真实 Azure EN→zh-Hans 与 zh-Hans→EN 成功 #44889928443](https://github.com/119shenhao/gambling/actions/runs/44889928443)：固定安全文本共预留39字符，未记录或暴露密钥。DEV D1 的原子预算更新后，一次性测试收据为 `pass`，provider=Azure，翻译每日5,000/月10,000，`settings.translation_enabled=true`。
- [数据库收据只读复核 #44890037912](https://github.com/119shenhao/gambling/actions/runs/44890037912)：`receipt=pass`，`budgetDayCharacters=39`、`budgetMonthCharacters=39`、providerBlocked=false。
- [DEV 线上配置再次复核 #44890627081](https://github.com/119shenhao/gambling/actions/runs/44890627081)：`workerEnabled=true`、`keyConfigured=true`、`translationReady=true`、`databaseEnabled=true`、`translationConfigured=true`，开发 D1 正常。
- [Cloudflare DEV 最终构建后 Secret 保留验收 #44891525065](https://github.com/119shenhao/gambling/actions/runs/44891525065)：Cloudflare build 完成后，Azure Key、开发 D1、Region、F0 标记及健康检查都正确。每次后续 DEV commit 的构建继续自动做这套 Secret 绑定验证；本次清理后的部署也必须通过。
- 成功后**永久删除**临时 `/api/dev/azure-smoke` 诊断接口及一次性 GitHub Actions，避免公开测试接口留在部署中；保留既有诊断日志和 D1 计费记录作为审计事实，不能将39字符测试当作真实帖子 UI/译文缓存端到端验收。
- 生产 `TRANSLATION_ENABLED=false` 仍然不变，且正式站尚未发布新论坛代码；不改动或导出生产密钥。

## 2026-11-21 论坛 UI / D1 缓存端到端验收

- [独立本地 D1 + 真 Worker HTTP API + 浏览器译文组件验收 #44892478870](https://github.com/119shenhao/gambling/actions/runs/44892478870)：全部 PASS。自动创建**仅本地测试数据库**的已发布帖子、列表摘要和回帖及 D1 翻译缓存，不在 Cloudflare DEV/PROD 产生人工帖子；按要求验证匿名缓存读取、再次请求不触发 Azure、原文语言不翻译、原文/译文界面切换、缓存加密解密、非法 locale 与旧版本拒绝，以及编辑原文后旧译文失效。开发环境此前真实 Azure Key 英中双向测试通过 #44889928443。
- 新增持续 `translation-local-e2e.yml`，源码/前端翻译代码修改时跑回归；本地测试脚本 `scripts/test-translation-local.mjs` 永远只使用 `wrangler.local.jsonc`（`APP_ENV=local`，假 D1 UUID）且不执行 `--remote`，所有固定文本和种子 SQL 在 `tests/fixtures/translation-local.sql`。
- 新增 `translation-dev-live.yml`，对当前部署执行只读内容和缓存查询、检查 Azure Secret/D1 启用状态；无原文上传 Azure，不额外扣除翻译额度，也不打印用户帖内容。正式站未发布，生产翻译保持关闭。

## 2026-11-21 管理员授权：已验证的统一身份认证中心 Owner（DEV + 生产预置）

用户要求其 Google 账号成为戒赌论坛开发、生产管理员。此前同一用户已经分别在 Identity Center DEV 和 PROD 完成了经过验证的首位 Owner 授权，**两个环境的中心 User ID 不相同**（真实 UUID 不在本公开项目文档重复披露）。

- `wrangler.jsonc` 新增非秘密 `ADMIN_CENTER_OWNER_SHA256`，DEV/PROD 分别保存与两套已验证 Owner 唯一对应的不同 SHA-256；不是 Google 邮箱或 sub，不能用于登录或伪造认证。
- `src/auth.ts` 仅在**有效的中心签名 JWT + 精确 Issuer、Client、Nonce 校验后**通过 `claims.sub` 触发匹配；`src/core.ts` 还会让已登录的旧会话在其下一次 API 请求时自动补授。授予前严格校验合法的环境/Issuer/Client、中心 UUID 摘要和本地 `auth_identities(provider='identity_center')` 既有绑定。匹配时幂等写入 `user_roles('admin')`，以及一次 `moderation_actions` 审计记录。其他账号、邮箱碰撞和旧 Google 直连均无法触发。
- **DEV** 当前 SSO 已启用，后续线上验收 `/api/me` 实际管理员角色（需要现有浏览器凭据，自动 CI 无法冒用用户 Cookie）；不要声称未检查远端 D1 时已经分配成功。
- **PROD** 目前 `119shenhao/gambling/main` 仍只有 README、无生产应用发布，Worker 正式论坛的 `IDENTITY_LOGIN_ENABLED=false`。本次仅在 `dev` 的未来生产配置预置匹配值，**没有修改、迁移、发布生产 D1 或 Worker**。未来正式发布并启用生产统一登录后，用户首次以正式 Identity Center Owner 登录会自动获得论坛 admin。不得声称目前生产已生效。
- 保留 Cloudflare Secrets、`keep_vars:true`、D1/R2 分离和全部已有站点功能。此功能只赋予已验证 Owner 一人管理员，不允许从用户提交的邮箱、昵称或账号 ID 自行授权。

## 2026-11-21 管理员角色实际授权：DEV 完成、生产预置

- 本轮用户明确要求 Google 账号为戒赌论坛 DEV/PROD 管理员。按 Identity Center 之前验证的两个环境 Owner ID 独立计算摘要，Forum DEV/PROD 对应 SHA-256 已写入 `dev/wrangler.jsonc`（不公开中心原始身份 ID、邮箱或 Google sub）。原统一认证中心验证过程（签名、issuer/audience/nonce）及 `identity_center` 用户映射不变。
- [权限回归 #44894045977](https://github.com/119shenhao/gambling/actions/runs/44894045977) PASS：本地隔离 D1 实测 Owner 旧会话自动领 admin、普通账号仍 member/拒绝管理接口、仅一次审计和幂等；未写生产。
- 为避免任何“权限等你下次登录才生效”的不确定性，使用仅限 Cloudflare **dev Preview** 的临时脚本对既有 `auth_identities(provider='identity_center')` 做**摘要匹配**；仅当恰好一个已验证 Owner、用户处于 active、D1 UUID/Issuer/Client 均严格匹配，才幂等插入 `user_roles(admin)` 并立即回读。没有匹配用户时构建必须失败，不准假报已授予。
- [Cloudflare Preview 强制回读构建 9b001975](https://github.com/119shenhao/gambling/commit/9b0019750d464ed4aba1c4f0b4c8531720406f9b) **success**；因为临时程序在构建阶段必须完成一次精确 OWNER 管理角色回读，否则构建报错，因此证实 **DEV D1 目标已验证 Owner 的 admin 角色存在**。生产 D1 未访问，其他用户未修改。
- 完成后**删除**临时授权脚本和构建调用，永久保留正式的签名 JWT + hashed Center Owner 角色匹配逻辑，之后不再运行 D1 强制初始化。Cloudflare Secret/D1/R2 严格隔离和构建后密钥守护继续启用。
- **生产仅预置代码配置，未完成真实授权**：仓库 `main` 目前只有 README，正式论坛尚未上线、生产 Identity Center 登录开关关闭。待用户单独确认正式发布并实际登录后，生产 Owner 通过相应摘要自动获得 admin，不跨库复制账号、不提前初始化生产管理员，也不得提前报告为已完成。

## 2026-11-21 戒赌论坛生产数据库管理员已实际授权并二次验收

用户要求现在完成戒赌论坛**生产环境的管理员授权**。生产 D1 现在已初始化完成，**不是仅预留代码/配置**。

- [一次性生产 D1 初始化/授权 #44895241936](https://github.com/119shenhao/identity-center/actions/runs/44895241936) PASS：精确校验 `gambling-community-prod` D1 UUID 与资源名后应用 21 项全新 schema 迁移；使用已验收 `identity-center-prod` Google Owner 的中心 User ID 作 SHA-256 精确匹配，仅在本论坛 PROD D1 建立对应 `identity_center` 身份映射和一个本地管理员角色，并回读验证 `user_roles(admin)` 恰好一人。保留 DEV/Spine 所有用户、帖子、Secrets，未跨环境复制数据。
- [独立只读二次回查 #44895483517](https://github.com/119shenhao/identity-center/actions/runs/44895483517) PASS：重新校验 Center PROD 已认证的 Google Owner、论坛独立 D1 的已关联账号、管理员角色唯一性、21 项迁移历史。
- 同时已在生产 Identity Center 登记 `gambling-community-prod`（`web_confidential`）及唯一精确回调 `https://gambling.nbn369.com/api/auth/identity/callback`。**目前 client 仍 disabled，尚无生产 Secret verifier**。这确保还未完成独立生产 OAuth 密钥握手时不能误开启登录。
- **权限存储状态：生产 D1 管理员角色已完成；生产网页登录还未完成。** 当前 `main` 仍只有 README，`gambling.nbn369.com` 只提供占位内容。后续需要部署生产论坛、配置**独立** `IDENTITY_CLIENT_SECRET` Worker Secret（不同于 Spine 和 DEV）、让认证中心登记对应安全摘要并启用客户端、最后启动 `IDENTITY_LOGIN_ENABLED=true`，用真实 Google 账户完成网页登录和权限验收。不要把这些尚未完成的工作说成已部署成功。
- 相关受控迁移脚本用后即停，后续部署不能重执行全量 schema 初始化，必须保持 Cloudflare `keep_vars:true`、生产 Worker 已保存的 `TRANSLATOR_KEY` Secret 和其他 Variables、R2/D1 绑定不变；生产翻译开关仍关闭。

## 2026-11-21 生产站首版已由 main 发布；管理员 D1 授权再次确认

- 正式 `main` 提交 [d57cb43bbabc7d2480ee54dc8a985fcf2a8b5cfb](https://github.com/119shenhao/gambling/commit/d57cb43bbabc7d2480ee54dc8a985fcf2a8b5cfb) 已包含论坛应用源码、生产 D1/R2 绑定与固定管理员 SHA-256，Cloudflare Workers Build 和主分支 CI 成功。**该发布保持 `IDENTITY_LOGIN_ENABLED=false`、`TRANSLATION_ENABLED=false`，未擅自开启生产 Google OAuth/翻译**。
- 生产站运行时只读验证 [Gambling Production launch readiness #44894827005 第二次运行](https://github.com/119shenhao/gambling/actions/runs/44894827005)：`https://gambling.nbn369.com/api/health` HTTP200 JSON `environment=production`、`databaseReady=true`；首页 HTTP200 `text/html`；Identity Center PROD health 正常。此前 first-run 收到 text/plain 的情况已由后续正式部署替代。
- [生产 D1 首次迁移、Owner 角色授权与客户端注册 #44895241936](https://github.com/119shenhao/identity-center/actions/runs/44895241936) 和 [独立只读二次回查 #44895483517](https://github.com/119shenhao/identity-center/actions/runs/44895483517) 成功：21 项生产 schema 迁移、唯一已验证中心生产 Owner 对应的 forum admin 角色确实存在；不复制 DEV/Spine 内容。
- 当前 Center PROD 的 `gambling-community-prod` 已注册单一回调，但仍 **disabled，且无有效生产 OAuth client secret verifier**。现有自动化 D1 token 对 Cloudflare Workers Script API 返回403，无权代写生产 Worker Secret。不能声称生产 Google 登录或管理员网页登录已成功。
- 以后要完成网页登录，只需单独为生产 Worker 设置高熵 `IDENTITY_CLIENT_SECRET`（不能与 DEV 或 Spine 共用）、在 Center PROD 登记 SHA256 base64url verifier、启用此独立 client，然后将对应生产 `IDENTITY_LOGIN_ENABLED` 置 true 并上线验证 `/api/me` 管理员角色。保持 `keep_vars:true`、不覆盖现有 `TRANSLATOR_KEY` 等 Secrets。
- 过时的首次上线 Draft PR [#3](https://github.com/119shenhao/gambling/pull/3) 已关闭，避免较旧 release 分支覆盖 `main` 已上线的版本。以后新的生产更改应从**最新 main** 定向修改，而非合并旧代码快照。


## 2026-11-22 开发环境 HTTP 采集与生产同步预备（尚未正式采集/同步）

用户要求参考 Spine 已验收模式：开发站以 HTTP 采集原文及回复写入独立开发库，生产库通过受保护同步作业一次性接收已发布、无回执的主帖及当时公开评论；另建 ChatGPT 每6小时采集、每12小时同步定时任务。

- DEV 代码已恢复预览专用 `/api/import/*`、`/api/collect/*`，添加 DEV `IMPORT_DB` 同 UUID 独立绑定（仅戒赌社区 DEV D1），正式 `IMPORT_ENABLED=false`、`COLLECT_ENABLED=false` 不变；`migrations/preview-only/0001_collector_queue.sql` 只在 DEV 构建迁移，不能进入生产迁移链。代码提交 [07c92f81](https://github.com/119shenhao/gambling/commit/07c92f81fbb16f01a24a5beeaf16b3d2d6f8a3da)，[CI #44976891166](https://github.com/119shenhao/gambling/actions/runs/44976891166) PASS。
- 独立同步 CLI、独立 Cloudflare D1 配置、安全的私有授权导出采集器和来源注册表见提交 [d4f4a2e6](https://github.com/119shenhao/gambling/commit/d4f4a2e608779f99fc3261f68d3f58efb0991bf6)；[CI #44976999174](https://github.com/119shenhao/gambling/actions/runs/44976999174) PASS。预览/生产 D1 UUID 经静态检查，内容指纹前缀为 gambling-topic-v1，不能与 Spine 混用。
- 开发分支新增 `.github/workflows/gambling-collector-on-demand.yml` 和 `.github/workflows/gambling-sync-posts.yml`，提交 [5f603eef](https://github.com/119shenhao/gambling/commit/5f603eefbac4ee5a4ad948262bd01786bff03dec)，[CI #44977060680](https://github.com/119shenhao/gambling/actions/runs/44977060680) PASS；没有在 Actions 创建自动 cron，也没有派发生产同步。
- ChatGPT 两项定时任务已经创建启用，采集每6小时（北京时间12:00起），同步每12小时（北京时间13:00起）；任务必须执行就绪门禁，未验收时仅报告阻碍。GitHub 源列表 `scripts/gambling_sources.json` 目前为空，不允许移植颈椎腰椎的医学数据来源与授权。每次真实采集须验证 parser，完整回复及去重/claim/complete 安全校验才允许启用。
- [DEV 采集只读请求 #44977172957](https://github.com/119shenhao/gambling/actions/runs/44977172957) SUCCESS，日志确认 Preview HTTP 就绪，`importEnabled=true`、`collectEnabled=true`，但 `registered_sources=0`，`new_topics=0`。这不是自动采集已有业务网站成功的证明。开发 HTTP 认领→释放的线上 Smoke 见 [#44977141531](https://github.com/119shenhao/gambling/actions/runs/44977141531)，须等待最终日志后另行记录结论，不能预先称通过。
- 正式生产内容同步未验收：受控 Workflow 仍仅在 dev 分支，首次 D1 dry-run、Time Travel、正式写入及新 Job 成功记录尚不存在；且 GitHub 独立 Secret `GAMBLING_PROD_D1_API_TOKEN` 和账号变量配置尚未验证。任务安全门禁禁止提前写生产。首次受控验收并按发布流程切换后，才可自动重跑已验证作业。
- 保留两个论坛所有 Cloudflare 变量、Secret、Identity Center 配置及独立 D1/R2；本次未更改 main、生产 D1 或公开生产登录/翻译开关。

详见 [COLLECTION_AND_SYNC.md](COLLECTION_AND_SYNC.md)。

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
- 采集定时任务每6小时仍处于启用状态，但 `scripts/gambling_sources.json` 仍无稳定解析的真实戒赌站点。后续只有配置好的来源才能运行真正定时采集。

## 2026-11-22 戒赌论坛独立采集器真实改造（GamCare 全文解析核验）

用户要求真正修复原定时采集源数为 0 的问题，且采集任务必须独立于 Spine。开发工作仅针对 `119shenhao/gambling/dev`：
- 新增 `scripts/gambling_forums.py` 与 `tests/test_gambling_collector.py`；改造 `scripts/gambling_collect.py`；更新本仓库独立采集 Actions。实现候选列表发现、真实 URL 稳定 slug、严格原文/回复解析、exclusions/claim/complete/release、回读验证、每站限制与错误计数。对可能缺失回复/分页/隐私泄露的帖子拒绝导入。
- `scripts/gambling_sources.json` 登记 `gamcare` 与 `gamblingtherapy` 两个独立来源。GamCare 的 `parser_verified=true` 仅表示一篇真实样本完成解析，不意味着所有帖子可成功。Gambling Therapy 列表 HTTP 403，暂未验收解析。
- [#44992825630](https://github.com/119shenhao/gambling/actions/runs/44992825630)：真实 Runner 访问开发 `/api/health` 成功、GamCare 两个板块合并 39 个去重候选；Gambling Therapy 返回 403；10 项离线测试通过，无数据库写入。
- [#44993018367](https://github.com/119shenhao/gambling/actions/runs/44993018367)：针对 `i-need-to-stop-before-i-loose-everything` 实际下载 GamCare 原帖，`parser_probe_ok`，完整识别 7 条回复；仅只读，不导入。
- [#44993097907](https://github.com/119shenhao/gambling/actions/runs/44993097907)：12 项 Python 单测通过，包括 mock HTTP/D1 的认领→complete→readback 和解析失败释放；真实 GamCare 7 回复探测再次通过。日志出现的 `imported` 是 **mock 测试输出**，不是 D1 真正写入；真实本轮 `new_topics=0,new_comments=0`。
- [#44993122908](https://github.com/119shenhao/gambling/actions/runs/44993122908)：Gambling Community npm 代码测试成功，修复了旧测试“来源表必须为空”的硬编码假设。
- 根据各站内容条款，没有证据表明当前可以将 GamCare/Gambling Therapy/Reddit 他人完整帖子与评论作为本站匿名原创自动转载。因此登记的来源仍 `approved=false`、`reuse_allowed=false`，`importable_sources=0`；自动 `collect` 必须安全报未就绪，不得假报成功。许可确认或用户自有可再发布内容是开启实际自动入库的剩余前置条件。
- 原独立 ChatGPT 每 6 小时采集任务和每 12 小时生产同步任务继续保持项目隔离；本轮没有修改 Spine 定时任务或生产同步作业、密钥、数据库内容。

**当前结论：** “自动发现、解析、API 编排”已经开发并经过局部真实/模拟验证；**外站全文自动发布未启用、DEV 新增 0**。只有经验证可合法再发布的来源满足上线门槛后才能声明自动采集正常运行。

### 2026-11-22 最终补测：分页回读
- 后续修复 `scripts/gambling_collect.py::readback`：详情 API 使用 `?before=<cursor>` 分页，每页通常20条评论；现在可完整回读并校验最多49条，避免导入21–49条回复时误把第一页当全部。
- [最终独立采集检查 #44993261146](https://github.com/119shenhao/gambling/actions/runs/44993261146) PASS：**13/13** Python 测试通过，含多页回读模拟；再次从 GamCare 真实网页只读解析 **7 条回复**，`new_topics=0,new_comments=0`。此次日志中的模拟导入提示属于 unittest，不是 D1 写入。
- [Gambling Community CI #44993261210](https://github.com/119shenhao/gambling/actions/runs/44993261210) PASS：项目综合检查完成。
- **尚未开启自动全文复制**：两站 `approved=false`、`reuse_allowed=false`；下一步需有允许完整再发布的确切来源，确认每站的许可及真实论坛文章结构，之后才能运行 `mode=collect` 验证开发 D1 新增记录。当前不要报告“已能自动导入2篇”。

## 2026-11-22 GamCare 用户确认许可后的真实 DEV 首次入库（最新）

- 用户在本对话确认已取得完整帖子和回复再发布许可。仅据此在 gambling/dev 的来源注册表对 **GamCare** 设 `approved=true`、`reuse_allowed=true`；原始凭证目前为用户确认陈述，尚未独立核验许可文件。Gambling Therapy 因 HTTP 403 和未核对复用范围仍关闭。
- [首次真实完整主帖导入 #44993497291](https://github.com/119shenhao/gambling/actions/runs/44993497291) PASS：GamCare “I need to stop before I loose everything”，DEV 新增 1 篇、7 回复，topic_id `11823542-8666-48ae-87e4-3e91cfe90a17`，接口回读通过。
- [自动发现首轮 #44993558005](https://github.com/119shenhao/gambling/actions/runs/44993558005) workflow 标记 failure：尽管 “Payday 2, 61 Days Gamble Free” 及 “Can't go on like this 3” **分别真实新增 1 篇、2 回复**（共 2 篇、4 回复），另外两篇已写入的长帖因服务端独立语言识别 `und` 与导入提示 `en` 不同而触发旧回读的误报。原文内容不应因语言检测标签不同被判错；待复核。
- 修复 `readback`：保留严格原文标题/正文、每条评论正文与条数、层级及多页回读验证；语言提示与服务端重新检测的差异单独记录 `readback_language_detection` 而非误判内容缺失；候选正文缺失、隐私风险等记录为 rejected，不影响成功采集的 Actions 退出码。
- [自动发现验证成功 #44993765907](https://github.com/119shenhao/gambling/actions/runs/44993765907)：15 项 Python 测试通过，GamCare 自动发现，新增真实 2 主帖、7 回复（“Hi I'm Karolina” 3 条、“10 Years On, 5 Days Off” 4 条），排除 5 个不合格候选，`errors=0`，工作流 Success。
- [历史两篇异常内容只读回查 #44993908744](https://github.com/119shenhao/gambling/actions/runs/44993908744) PASS：GamCare “New Start for 50”（topic_id `a01e9483-79b9-45e7-9725-7157087dcf23`）原文及 **14 回复**全部回读一致；“Stuart – Well Done on a Year GF”（topic_id `f20ca546-8f1a-4b87-823a-af953bebbdea`）原文及 **7 回复**全部回读一致。仅 `source_lang` 服务端自动识别不同，保留检测结果。该验收未重复导入。
- 已确认合计 **7 篇主帖、39 条回复**真正导入 DEV 并回读核验（1+2+2+2 篇；7+4+7+21 回复），不包含历史 [QA DIGEST] 摘要测试数据。没有写生产库。
- 旧 JS CI 在 GamCare 开启后仍假设所有来源 `approved=false`，导致 [#44993908750](https://github.com/119shenhao/gambling/actions/runs/44993908750) 失败；已修改为只允许已确认的 GamCare 标志为 true，其余来源必须继续 false。后续检查最新 CI 结果确认修复完成。
- 独立 ChatGPT 每6小时采集任务与每12小时生产同步任务保持隔离；本轮没有触发生产同步，新的真实 DEV 帖子尚不能声称已发布正式站。

### 2026-11-22 最终自动采集复测（覆盖本节上一版统计）
- [恢复默认模式正式采集 #44994042299](https://github.com/119shenhao/gambling/actions/runs/44994042299) 已完成成功：GamCare 又新增 **2 篇真实主帖、10 条真实回复**（`i-have-joined-up` 3 条、`scared-2` 7 条），5 个缺失回复或涉及需保护信息的候选正常拒绝、`errors=0`、`duplicates=0`；Gambling Therapy 来源未启用，正式采集没有再发起访问其403的请求。
- [该提交整体 CI #44994042376](https://github.com/119shenhao/gambling/actions/runs/44994042376) PASS，独立 Python 解析与编排单测 17/17 通过。上方已有7篇39回复是之前的真实里程碑，本次新增后 **累积9篇真实 GamCare 主帖、49条真实回帖**，不包括此前QA测试数据；9篇均经当轮回读或历史只读审计通过。
- `.github/gambling-collector-request.json` 已恢复为常规 `mode=collect, sites=["all"], candidates={}, limit=2`。ChatGPT 每6小时戒赌论坛独立定时任务继续开启；不使用 Spine 的定时器/脚本/密钥。此轮操作限定 DEV D1，不直接操作正式数据库或生产发布。生产同步属于另一个独立的既有定时任务。
- 用户的 GamCare 完整帖子和回复再发布许可为用户对话内声明，`scripts/gambling_sources.json` 如实记录；没有将此声明扩展到其它站点，也没有将它说成独立审验的书面许可证。系统导入账户为 Anonymous，`collect_sources` 保留来源站点与原始稳定 ID。

## 2026-11-22 戒赌社区酒红与金色界面（DEV）

- 视觉参考为 Crime Life Simulator Docs 镜像中的 Casino Life Simulator 赌场大厅。论坛沿用酒红、暖金描边和菱形纹理，用静态 CSS 表现。首页展示已有的本地化站名和口号，正文与评论使用纯色阅读面板。
- 默认阅读配色改为深酒红色，个人中心仍可切换柔和暖色并调整字号。手机导航保留四个入口，搜索、帖子和弹窗使用同一套主题。
- 本地 TypeScript、25 项测试、独立本地 D1 迁移检查和版本化前端构建均已通过。
- [GitHub CI #44995255890](https://github.com/119shenhao/gambling/actions/runs/44995255890) 与该提交的 Cloudflare DEV Preview 构建成功。开发站已实际响应前端版本 `03d96c1105bbfb51`。桌面浏览器检查了英文与简体中文首页、帖子详情和回复展示、搜索入口、访客发帖登录弹窗、暖色配色及字号切换。iPhone Safari 真机视觉验收待补。

## 2026-11-22 采集长帖改造：每篇最多500条真实回复

**用户确认规则**：不能因为有50条或更多回复而放弃整篇主帖；外站实际不超过500条时逐页采集全部回复，超过500条时**按原站顺序仅取前500条（第501条不保存）**。评论和楼中楼合并计数，保留可验证的父子关系；如缺页/正文丢失则拒绝该候选，不能谎称“完整”。

- 仅在 `119shenhao/gambling/dev` 增加 `scripts/gambling_forums.py::parse_topic_pages`：按GamCare原帖 `/paged/N/` 连续读取，校对全站显示的帖子总数（扣除主帖），限制前500回复、页数上限按500条目标动态计算（不再设置40页的额外过滤门槛）；记录 `source_total/capped/pages`。首次真实演练直接读取2页25条，后又读10页142条。
- `scripts/gambling_collect.py` 新增分批编排 `complete_staged`，原单包不超过49条继续走旧 `collect/complete`；跨页或大帖采用 `/api/collect/long/start → append → finish`，每批10条；完成后对DEV API全部评论分页回读，最高500条。源帖已完成/指纹重复时跳过。
- `src/collect-long.ts`：独立DEV长期暂存元数据与回复，单次上传最多20条，offset必须连续、支持相同批次重试和跨批parent_index。只在全部 `target_count` 条暂存且验证序号无缺口时，用**一个D1事务**创建主帖、最多500评论、source完成回执，不能公开半成品。暂存表 `migrations/preview-only/0002_collector_long.sql` 限定 ordinal 0至499，记录 `source_total` 和 `capped`；仅开发预览自动迁移，**不在生产迁移链**。
- [GamCare两页25回复真实DEV入库 #44995042695](https://github.com/119shenhao/gambling/actions/runs/44995042695) PASS：topic_id `e4439865-eef8-4932-a888-c5d99c722c52`，新增1主帖、25回复，回读数量与原文匹配。
- [GamCare十页142回复真实DEV入库 #44995221312](https://github.com/119shenhao/gambling/actions/runs/44995221312) PASS：topic_id `f9d8e0d6-b6b3-46b8-a957-5347db346513`，新增1主帖、142回复，回读通过。证明大于49条不再自动拒绝。
- Python单测覆盖：GamCare两页、原站501条时恰好截取前500不含第501、缺失分页拒绝、preview SQL 500条上限阻止第501写入；新服务端配置、TS CI也通过独立检查。**501封顶已通过程序/SQL测试，但尚没有成功的真实超过500条帖子入库验收，不能夸大。**
- [Charly's life >500回复只读探测 #44995338423](https://github.com/119shenhao/gambling/actions/runs/44995338423)：因源网页某条回复 `empty_post_or_reply` 无法取得完整正文而安全拒绝；未入库，并非因超出500直接跳过。此问题属于真实来源可读性，后续可定位/改进，但不能编造丢失回复。
- 已更新 ChatGPT 独立「戒赌论坛独立采集入库」每6小时任务指令支持分页500上限；不触碰独立的Spine任务或本论坛生产同步任务。

**状态**：开发环境已证明能真实入库跨页142条；500封顶逻辑已编码、单测验证，仍需要一篇可完整读取、实际>500回复的外站候选，做完整端到端采集验证。生产D1未因本次开发改动。

### 2026-11-22 恢复正常自动采集后的最终验收

- [常规自动发现采集 #44995511035](https://github.com/119shenhao/gambling/actions/runs/44995511035) PASS：请求文件恢复 `mode=collect,sites=[all],candidates={},limit=2`，新增 GamCare 2篇真实主帖和7条回复（`day-1-here-we-go` 3条、`do-i-love-risks-not-winning` 4条），`errors=0`，不合格候选6篇正常跳过。
- 本次500上限改造累计本轮真实新增4篇：两页25条、十页142条、常规自动发现2篇共7条；连同此前9篇49条，**DEV中已核实合计13篇GamCare真实主帖、223条真实回复**（不含历史QA测试）。
- [最终代码CI #44995565242](https://github.com/119shenhao/gambling/actions/runs/44995565242) PASS；独立开发环境线上只读烟测 [#44995565253](https://github.com/119shenhao/gambling/actions/runs/44995565253) PASS。
- 独立ChatGPT采集任务说明同步改为：最多500条，超过只取前500，501不写；既有每6小时频率、DEV目标、独立仓库和原任务ID不变。
- 特别说明：**真实501条以上帖子到DEV并保留恰好500条的端到端验收尚未成功取得可用外站候选**，但上限与分页截断已通过模拟500/501条、preview-only SQLite约束以及实际142条跨页入库验证。此前源帖`charlys-life`因源正文出现空回复而被排除，与500上限无关。

## 2026-11-22 戒赌社区深绿阅读面板与紧凑首页（DEV）

- 移除首页站名与口号大卡片。顶栏继续显示站名，目录导航后直接进入「最新讨论」；主标题改为帖子列表标题。
- 默认主题改为酒红顶栏和导航、深绿帖子卡片、正文与评论面板。静态菱形纹理移至顶栏，暖金突出发帖与选中状态。保留现有暖色配色和阅读字号设置。
- [GitHub CI #44996087082](https://github.com/119shenhao/gambling/actions/runs/44996087082) 与 Cloudflare DEV Preview 构建通过，线上前端版本为 `9a98aedd54a33389`。本地 25 项测试和独立 D1 迁移验证通过。
- 用开发站资源在 Chromium 验证了 1366px 桌面和 320px、390px、430px 手机宽度。最新讨论直接衔接导航，四个导航入口完整，首页无横向溢出，首帖在首屏可见。390px 使用模拟管理员布局，另验证了帖子详情、回复面板和暖色配色切换。iPhone Safari 真机尚未实测。

## 2026-11-22 已选定移动端戒赌社区视觉方案

用户选定酒红/深绿台布/克制暗金的移动端界面图作为后续统一 UI 基线。已将 `dev` 分支 `public/styles.css` 的手机导航、帖子卡片、标题与排序、顶部配色、移动间距和按钮色彩调整为该方案，并在 `public/index.html` 换用金色黑桃品牌图标；新增静态 UI 回归测试。现有四个导航入口、发帖、账号、阅读偏好、帖子操作的逻辑不变，暖色阅读主题不被暗色卡片样式覆盖。

这属于**开发分支源码变更**，不等于已完成线上视觉验收或生产发布。仍需 CI 检查及真实手机浏览器检验：360/390/430px 宽度、语言切换超长文本、未登录/登录态、3 行摘要、点击操作、帖子长文与楼中楼、warm 主题与大字号。上线必须另行遵循用户生产发布许可。



## 2026-11-22 移动设计对照截图后的第二轮修正

用户提供真实开发站 384px 移动截图，与此前选定的竖屏设计稿对照后，指出视觉实现仍明显不同。本轮针对真正看到的差异修正，而不是重新生成美术稿：

- 移动端开发环境标记原先单独占据第二行：现在仍保留在 DOM 供辅助技术读取，但视觉上不再撑高页头；开发环境地址保持不变。
- 管理员账号额外的「社区管理」占据导航下方一行：手机端隐藏侧栏该入口，将「社区管理」加入登录用户的账户菜单；桌面端仍保留侧栏管理入口。不取消管理员权限。
- 调整酒红背景更接近设计图，降低密集菱形纹理；将原偏深青的帖子卡片改为偏绿毡的深绿色、柔和金边、克制阴影，并保证暖色阅读主题独立。
- 手机导航去除厚重整框，保留原有四按钮功能及选中态，增加轻分隔线；「最新讨论」前使用细金线与小黑桃作为分隔，不再把黑桃悬空置于大段留白内。
- 默认字号时帖子标题由 22px 缩到 20px，摘要由 16px 缩到 15px，减少每张卡片的空白；用户主动选择较大或最大字号时不覆盖其偏好，移动摘要仍为三行截断。
- 文件：`public/styles.css`、`public/app.js`、`tests/gambling.test.mjs`。本次仅提交 `dev`，无生产或数据库变更；待真实手机线上视觉验收，不能宣称与设计稿完全像素一致。

**回归重点**：384px 主屏首帖的位置、360px 与 430px 宽度、管理员入口新位置、匿名用户登录、简体/繁体/英文下导航是否溢出、暖色阅读/字号设置、摘要三行和楼中楼排版。

## 2026-11-22 MoneySavingExpert 实际入库、待审核回复验收（DEV-only）

- 经用户在项目会话确认该站完整帖子与回复再发布授权，来源登记 `moneysavingexpert` 在 `scripts/gambling_sources.json` 的许可和解析门禁已开启。许可依据是用户陈述，未独立审核书面协议。仅启用赌博项目独立 DEV 环境，不迁移生产。
- 解析器 `scripts/gambling_mse.py` 修复 Vanilla 论坛内嵌表情/图片误判：表情保留 alt、正文图片保留 HTTPS 引用；验证严格分页、源站数字ID去重、原顺序前500回复封顶。真实只读解析 #44998125442：原站 67 回复全读；原站 632 回复取前500。站内搜索接口 HTTP 403，当前以已核对的讨论种子和栏目分页作为发现后备，不能声称已经解决跨全站的稳定新帖发现。
- **首次实写工作流 #44998576176**：真实 DEV 新增 2 篇、501 条评论，其中原站 632 回复的长帖 DEV 保存500并完成回读，另一篇保存1；此工作流总体 Failure 是因为源ID `6200242` 的 67 回复帖回读仅 65 条可见，旧代码把隐藏审核误作漏采。该帖实已完成写入，不能重复 claim。
- **原因查明**：源帖 `6200242` 的 67 条在独立 DEV D1 已全部存储，公开接口仅显示 `published=65`；两条为 `pending_review=2`（原帖第5、52条，分别有3、4个 URL，链接阈值触发）。只读探测 #44999947418 检查了 67条原文、可见65及审核分类，未修改内容。
- **用户确认规则**：待审核评论计入**已成功入库**，但在审核通过前不强制公开。为避免仅凭差额误判，`/api/collect/verification?site=...&source_id=...` 在 DEV **仅返回已完成来源、topic_id和实际 D1 按状态计数**，不暴露待审核正文/作者。采集端要求完成回执、确切 topic_id、D1 总数=目标数、公开内容逐字一致、公开量+待审核量=目标数，且没有 blocked/deleted/未知状态，才能判定通过；否则仍报错。
- **真实修复复验 #45000202855 成功**：`completed_audit_ok`、`readback_pending_review_verified`，核对 topic_id `7d5b2d38-287a-4c6c-801b-fb1be7c9979d`、stored=67、public=65、pending_review=2；无重新写库，`errors=0`，35项 Python 单测通过。JS/TS 综合 CI #45000202813 成功。
- 每6小时的 ChatGPT 独立采集日程未更改，生产 Worker、生产 D1、`main` 和 spine 论坛均未操作。本节的统计是各次运行各自新增，不可把历史成功帖子重算一次。

### 2026-11-22 待审核验收修复后的正式采集回归

- [正常采集 #45000258945](https://github.com/119shenhao/gambling/actions/runs/45000258945) **Success**：恢复 `mode=collect,sites=["all"],candidates={},limit=2` 后本轮独立 DEV 新增 **4篇主帖、26条回复**，`errors=0`、`duplicates=0`，8个不合格候选安全跳过；其中 GamCare 新增2篇7回复，MoneySavingExpert 新增2篇19回复。工作流的 unittest 中 `imported` 事件仅为模拟，真实入库计数只以运行末尾 `site_summary/run_summary` 为准。
- 真实 MoneySavingExpert 本轮新增：源帖 `6655256` 7回复、`6035505` 12回复，正常回读通过。此前 `6200242` 已经是完成回执且已核对DB总数67（65公开+2待审核），未重入库、没有重复计数。新验收规则不改变管理审核状态，也不会把待审核评论显示给访客。
- 自动采集任务原有**每6小时**频率与各启用来源每轮最多2篇保持不变，正式生产环境不动。MoneySavingExpert 网站搜索返回403；当前主要依赖种子和栏目列表，已知种子经采集后可能耗尽，不能据此宣称长期稳定发现新帖；后续需要继续拓展可靠的公开发现途径。


## 2026-11-22 V2EX 中文来源真实采集与251条回复回读验收（DEV）

- 已完成V2EX公开主题 `https://www.v2ex.com/t/1121755` 的严格三页解析，原站显示251条回复，分页100+100+51，共251；新解析器对联系邮箱/电话等文字作适度脱敏，保留其余正文与原始回复顺序，45项Python单元测试成功。只读解析 GitHub Actions [#45003064070](https://github.com/119shenhao/gambling/actions/runs/45003064070) 报告 `parser_ok, source_total=251, captured=251, pages=3, capped=false`。
- 用户已确认V2EX完整主帖和回复有权复用，用户声明记录在 `scripts/gambling_sources.json`；该来源的 `approved`、`reuse_allowed`、`parser_verified` 已全部为 `true`，仅开发环境采集。
- **实际开发D1入库并成功只读回读**：使用原有 `gambling-collector-on-demand.yml` 对V2EX `1121755` 发起首次真实导入，随后 [完整回读验收 #45003490694](https://github.com/119shenhao/gambling/actions/runs/45003490694) 显示 `completed_audit_ok`、`replies=251`、`topic_id=5aae46c6-56d8-468d-8d24-76bc689f09d2`，`errors=0`，并验证原文、所有回复数量、顺序及公开正文；同一源已在DEV exclusions中记录完成，后续不会重复导入。**这次审计本身新增0篇0条，251条是此前实际写入的旧记录**；不要把审计再次计为新增。
- 由于GitHub连接器查询push-triggered Actions存在局限，已在同一采集工作流增加脱敏结果写回 `docs/GAMBLING_COLLECTOR_LATEST.json`；仅记录运行ID、来源ID、聚合数和topic_id，不复制用户正文、邮件、电话号码和lease_token。可据此直接回读后续采集运行；不会另建GitHub Actions定时器。
- **已恢复常规 `.github/gambling-collector-request.json`**：`mode=collect`、`sites=["all"]`、`candidates={}`、`limit=2`，请求提交SHA `2d0533f1e2b54e5b5f22f9e4fab11a6e09b36f01`。既有ChatGPT每6小时独立采集任务自动包括3个已启用站（GamCare/MoneySavingExpert/V2EX），其余来源保持禁用。恢复后的第一轮全来源实际运行结果须单独回读报告，不可预先宣称通过。
- 严守开发/生产隔离：本轮开发、采集和验收都只针对 `119shenhao/gambling/dev` 和其专有DEV D1；未触发正式发布或生产数据写入，未修改每12小时生产同步任务。豆瓣仍待后续单独开发。

## 2026-11-22 发帖按钮独立视觉强调（移动端）

用户对比实机截图后确认：仅让导航第4项「发帖」与前3项明显区分，但不要前一张金光闪烁、徽章装饰的华丽效果。最终采取**更深的墨绿色微渐变、粗体发帖文字、略厚的柔和暗金边框和极轻的内侧高光**；原位置、尺寸、文案与加号不变，其余导航、帖子卡片及功能不变。仅在 `dev/public/styles.css` 添加针对手机默认深色主题的局部覆盖，保留暖色阅读主题及其它语种；未修改 `main`、生产 Worker/D1 或任何同步/采集任务。需在开发预览真实手机端验收显示效果，暂不把已提交称为已部署成功。

## 2026-11-22 品牌图标改为骰子（开发环境）

用户明确要求将「戒赌社区」标题前的金色黑桃改为**金色骰子**。仅替换 `public/index.html` 的品牌 SVG（五点骰子，轻微倾斜），保留图标原有外框、色调、尺寸、位置，页面其余黑桃分隔装饰、发帖按钮和功能不动。已更新 `tests/gambling.test.mjs` 对品牌图标的静态断言。改动仅在 `dev`，不涉及生产、D1、采集或同步。开发站仍需确认最新构建已上线及手机端实际视觉效果。


## 2026-11-22 3号动感骰子正式接入 DEV

用户在 12 款骰子方案中选择「3号动感骰子」，并对顶部移动端视觉效果图表示满意，明确批准接入开发论坛。用可缩放的独立 `public/dynamic-dice.svg` 实现静态金色立体骰子与环绕金轨迹；`public/index.html` 品牌区只把先前平面的五点骰子换为 `<img src="/dynamic-dice.svg">`；`public/styles.css` 为其提供适配现有 35px 手机外框的 31px 显示尺寸。不修改任何帖子、按钮、导航、登录、翻译、采集、同步等功能。

相关静态回归检查位于 `tests/gambling.test.mjs`，构建脚本继续使用既有 TypeScript + node:test 校验。**变更仅提交 `119shenhao/gambling/dev`；正式站、生产 D1/R2 和 `main` 不动**。开发预览最新 Git 提交是否已自动部署、iPhone 实机视觉是否符合图稿，需要分别核实，不得把源代码提交直接写作部署验收。

## 2026-11-22 动感骰子实机截图纠偏（必须遵守）

用户上传的开发环境截图 IMG_3724.jpeg 显示此前手工重新绘制的 public/dynamic-dice.svg 与已选择的第3号动感骰子不一致：骰子面、旋转环的前后层次和比例错误。用户明确要求开发者必须先自行视觉对照检查，再发布到 DEV。

**修正方式**：从先前经用户选定的「12款骰子方案对比图」的第3号图标中原样裁出插画，按手机头部真实显示尺寸做圆角透明化与适当压缩，作为自包含 SVG 内嵌的 PNG 图像；不是重新手绘矢量 SVG。保留原画骰子的角度、点数、金色环绕轨道及方形金边，不使用先前有问题的手绘路径。取消原 .brand-icon 容器上的重复金边和底色（覆盖深色及暖色两套主题，注意 CSS specificity），维持原站标题、按钮和页面布局不变。

**发布前本地视觉验收**：已将提取图标放入用户最新截图的原品牌位置，查看 /mnt/data/dice_3_approved_preview.jpg，并使用 CairoSVG 渲染了最终图标，确认效果与第3号原画一致；检查 35px 手机导航图标大小。新增 Node 静态测试核查 PNG 签名、像素尺寸、原图数据与 CSS 去重边框要求。仅在 119shenhao/gambling/dev 提交，未修改主分支、生产网站、生产 D1、采集或同步。Cloudflare 远端构建/实机线上最终状态如果无可用回执必须保持未确认，不得以 GitHub 提交替代部署验收.

### 2026-11-22 同次修复：缓存版本与部署复核

为避免开发站浏览器继续缓存先前不准确的 /dynamic-dice.svg，已把从原始第3号图裁得的素材复制为新的 public/dynamic-dice-option3.svg，首页品牌处明确引用新 URL，并同步更新静态回归测试。保留旧文件但页面不再引用它。新素材内嵌 PNG 原始图案（80×80，2608 字节，Adler-32 3778e64c），经源码回读、源图数据指纹比对、圆角/金边仅一层的 CSS 优先级检查通过；本地 CairoSVG 解码渲染及用户截图替换预览均已检查。未能通过现有工具访问 Cloudflare Preview 实时页面，因此 Cloudflare 构建完成与实际手机线上呈现仍待独立回执；不得把 GitHub 提交或本地预览写成线上验收。

## 2026-11-22 三号动感骰子右边金边缺失：最终修复

用户在 17:48 iPhone 开发站截图中指出 3号动感骰子外圈金边右侧不完整。此前 80×80 的量化裁切图 `public/dynamic-dice-option3.svg` 把原画金边紧压图片边界，局部圆角/降采样导致视觉缺口；不能再把原文件原样缩放视为修复。

本次从最初「12款骰子方案」第3号原画高分辨率方形裁图重新制作：保持骰子的所有面、点数、金色环绕轨迹不动；在独立图像中留出四周透明安全边距，以匹配原画曲线的细金描边补足边框连续性（不在 CSS 额外套第二个边框），生成 `public/dynamic-dice-option3-complete.svg`。文件内嵌 128×128 PNG，SHA-256 `1984f8b12032bd157c5e48f420130afbaada50511614ca4cf81f32515d5574c3`，对比旧版 80×80 图像，右侧金边现在完整并与画面边缘隔开。首页 `public/index.html` 指向**新的文件名**，避免缓存旧图；CSS 现有两主题去重边框逻辑不变。

**改动范围**：仅 `119shenhao/gambling/dev` 的品牌资源、首页引用、静态回归测试和文档；不修改 `main`、生产 Worker/D1 或论坛业务逻辑。已在本地使用 Chromium/Playwright 按 390px 手机 CSS 视口、DPR=3 的 35px 图标实际渲染检查，并与用户选定原图、此前错图对照，确认源素材完整。Node 回归测试同时检验新资源名称、128×128 PNG 和固定 SHA-256，防止未来误用缺边的旧图。**云端在线 URL 当前无法通过可用工具访问，Cloudflare 自动构建、真实站部署、Safari 实机最终显示仍需线上回执，不可将本地验收表述为线上成功。**

## 2026-11-22 Casino 赌场大厅原生菱形背景移植（DEV）

按用户明确同意，使用 `119shenhao/crime-life-simulator-docs/main` 的**真实源码**：`source-mirror/project_inner_game/casino_life_simulator/assets/diamond-tile.svg`、`styles.css` 的 `.background-light`。已在戒赌社区 `dev` 添加**字节内容一致**的 `public/casino-diamond-tile.svg`；更新 `public/styles.css` 深色主题下的 body 和 topbar，使用 91×103 方片的比例缩放及原赌场中心柔光/左右黑红暗角/纵向阴影叠层，取消旧的 CSS 交叉线纹理。该背景静态平铺以免影响持续阅读。暖色阅读主题、3号骰子品牌素材、导航按钮、深绿帖子卡片及全部业务逻辑保留。测试 `tests/gambling.test.mjs` 增加原 SVG、配色、比例、渐变和暖色主题的回归断言。

本轮**仅提交 `119shenhao/gambling/dev`**；`main`、生产 Cloudflare Worker/D1、帖子采集/同步和 Identity Center 不变。GitHub Actions 与 Cloudflare 预览部署需另行检查运行回执；如果无法读取真实开发站，不把源码提交或本地静态预览表述为线上验收。


## 2026-11-22 · V2EX 语言标记 DEV zh-CN / PROD und 根因核对

- 用户截图确认：同一原帖 V2EX `1121755`（DEV topic_id `5aae46c6-56d8-468d-8d24-76bc689f09d2`，251 回复）在 DEV 首页显示 `zh-CN`，而已同步到 PROD 的版本显示 `und`。
- 已核对 `main` 与 `dev` 的 `src/source-language.ts` **blob SHA 一致**（`9c92f6901ed443d16bd37e459d3830f625302bc1`），两边均使用 `tinyld/heavy` 加中文字符判断，**不是不同语言模型**。
- 根因在数据链：旧版 `src/collect-long.ts` 的长帖分页 `finish` 向 `topics/comments` 写入 `source_lang=zh-CN,source_lang_mode=auto` 后，未向 `content_language_verifications` 写入对应内容版本的识别凭据；而已审核的 `scripts/sync-preview-to-production.mjs::resolveSyncLanguage` 只接受版本匹配的 `tinyld-heavy/azure-auto/admin-manual` 验证记录或手动语言，缺少时将发布语言回退为 `und`。截图与这一代码路径一致，但数据库中是否真的缺失凭据仍需 D1 只读验证后最终落锤。
- 在 DEV 源码提交 `0335bbc35ddc389478393849e0e557c6bbdcec72` 中，长帖 `finish` 现将已识别出的主帖及已发布回复的当前版本 `tinyld-heavy` 语言凭据与原文写入同一个 D1 batch；回归断言提交 `1a94b1d6d3b981b5a569cd665334439c0dcd7bbe`。**尚未取得本次修改的线上 CI/部署验收，不能把源码修复说成生产已修复**。
- **历史数据需要单独、准确的元数据修复**：先只读核对 DEV 原帖和 PROD 副本的 `source_lang/source_lang_mode/content_version`、对应语言验证记录、源 ID 和回复计数；仅对核实为中文原文且 PROD 为 `und` 的记录（回复逐条独立判断）修复原文语言标记和凭据。保持标题、正文、251 条回复、parent ID、作者、时间、状态、同步回执全部不变。因为该贴已同步且已有 receipt，原有一生一次同步工作流不会自动重新写入此篇，不可通过重复触发发布任务期待自动修正。
- 生产 D1 元数据写入需要单独确认授权，并通过受保护通道先核实 Time Travel 恢复点、执行定向更新及读回验证；不能用前端临时隐藏 `und` 代替真实数据修复。


## 2026-11-22 · 原文语言 DEV 单次识别、PROD 纯复制：仅戒赌论坛开发代码

用户最终确认：DEV 采集识别一次，语言字段与当前内容版本的验证记录一起原子保存；DEV→PROD 同步只核对，两者一致原样复制；缺失或冲突先在 DEV 修复；永不将已有有效语言静默降级为 `und`。用户再次强调**只处理戒赌论坛**，禁止碰 Spine。

- `scripts/sync-preview-to-production.mjs` DEV 提交 `aaf7580e0405fd234f969425730ccb6d01285762` 将静默回退改为明确 `source_language_proof_missing_or_stale` / `source_language_proof_conflict`；DEV 已知语言、版本、验证方法、验证语言须一致，否则在写入前终止，不做第二次识别。后续 `2ef6dbffa2eeb25cc29b85420f2b399fcb4399aa` 将校验提前到已有生产同内容帖的回执处理之前，避免绕过检查。手动标记保持显式选择，不伪造模型凭据；真正未知语言允许保存 `und`。
- 已有 `src/collect.ts`、`src/import.ts` 正常导入时，原文语言和有效凭据写入同一 D1 batch；`src/collect-long.ts` 之前的 V2EX 长帖漏写缺陷已在 `0335bbc35ddc389478393849e0e557c6bbdcec72` 修复（DEV 提交，需远程验收）。
- 新增 `scripts/repair-preview-language-proofs.mjs`，仅操作 `gambling-community-dev`，通过 `src/source-language.ts` 原始 `tinyld-heavy` 实现独立复核已识别但缺失凭据的 DEV 历史帖和回复；只有重新识别与既有 `source_lang` 一致时才允许 DEV 补写凭据，已有冲突记录不自动覆盖。默认只读，`--apply` 须设置具体开发 D1 ID 确认值，写后读回。不迁移/重导正文或回帖。
- `tests/sync-behavior.test.mjs`、`tests/gambling.test.mjs` 已加入跨语言、旧凭据、冲突、长帖、预览库限制和禁止二次检测测试；`docs/LANGUAGE_SYNC_RULES.md`、`docs/REQUIREMENTS.md` 已记录最终规范。
- **代码提交不等于远程生效**：CI 状态、受保护执行器固定代码升级、DEV 旧数据实库审计、PROD 历史 `und` 修复目前均需分别验证/批准。已有 PROD 受保护执行器仍固定审核提交 `94dded5100fd3d3ecc1758f9fba13d82be04c694`，**不会自动切换到本次 DEV 修改**；不得改自动同步任务频率或冒充生产已经修复。


### DEV 识别凭据与审核状态隔离（2026-11-22 补充）

- 后续代码检查发现：旧版只有 `status='published'` 才附上语言验证记录。待审核或被阻止的内容即使已在 DEV 独立识别，管理员以后点击发布仍可能缺凭据。现在在 DEV 把“识别及凭据存储”与“公开状态”分离：`src/language-state.ts` 的版本/非删除守卫、`src/collect.ts`、`src/import.ts`、`src/content.ts`、`src/collect-long.ts` 在单一 D1 batch 内保存识别出的语言与对应凭据；不会因此提前公开待审核/屏蔽内容。
- 最新相关提交：`f55569c9`、`e097f0a6`、`78cc09da`、`7ffca580`、`c10235f0`、`1e9c3ef1`。回归静态断言：`tests/gambling.test.mjs` 的 `58ea894a`。
- 所有改动仍仅在戒赌论坛 `dev`；实际 GitHub Actions `ci.yml` 的最新结果未获取，不能提前宣称验收通过。既有 Identity Center 受保护生产同步执行器固定旧 SHA，尚未改动，生产 D1 已存在的 `und` 也未修改。


## 2026-11-22 戒赌论坛原文语言修复：生产验收完成（优先于前述旧待验收记录）

用户明确授权只处理戒赌论坛，开发→生产同步继续每12小时自动执行，不修改 Spine、OAuth、D1结构、密钥或帖子原文。

- 原因：V2EX 大帖入库保存了 DEV `zh-CN`，旧版长帖流程没有同步保存当前版本语言凭据；旧同步器因此将已识别语言静默改为 `und`。已在 DEV 修复所有导入路径（普通/长帖/待审核）语言与验证记录的同 D1 batch 保存。新的同步代码固定在 `09df153ce9fdc57b435adf92b2aceeea393f3678`，只核对语言标记、对应版本和方法，缺失或冲突报错，不执行语言识别模型，不降级已识别语言。
- 一次性历史修复 [Identity Center Actions #45024860737](https://github.com/119shenhao/identity-center/actions/runs/45024860737) **success**：DEV 补齐并读回863条证据；PROD 修改并验证6篇原帖、857条回复的错误 `und`；包括 V2EX 主题 `5aae46c6-56d8-468d-8d24-76bc689f09d2` 的 `zh-CN`。源文、回复树、作者、时间及同步回执未重导、未改变。
- 用户手动采集 [#45025631325](https://github.com/119shenhao/gambling/actions/runs/45025631325) **success**：新增2篇/5回复、errors=0；随后手动触发新的受保护同步 [#45026829285](https://github.com/119shenhao/identity-center/actions/runs/45026829285) **success**，日志 dry-run `examined=2,new=2,comments=5`；apply `new=2,comments=5,marked=2`；下一轮 `examined=0`，最终 `examined=0`。新版生产复制与源回执实际验收通过。
- 正式站在线检查 [#45027269679](https://github.com/119shenhao/gambling/actions/runs/45027269679) **success**：正式 Worker `GET /api/health` 返回版本 `0.5.1-language-proof-atomic.20261122`、数据库 ready，正式 `GET /api/topics/5aae46c6-56d8-468d-8d24-76bc689f09d2` 返回原文 `zh-CN`；SSO 和 Azure 设置检查正常。相应可复查报告 `docs/GAMBLING_PROD_LANGUAGE_LIVE_LATEST.json`。
- 剩余142条历史 `und` 已通过受保护只读检查 [#45026992693](https://github.com/119shenhao/identity-center/actions/runs/45026992693) 全量确认：DEV 原始 `source_lang` 也是 `und` 的回复142条，**不是同步把已识别的语言降级**；DEV 来源缺失、DEV已识别而验证缺失、生产内容不一致、生产验证冲突均为0。长度分布：≤8字符19、9–30字符58、>30字符65。由于没有经过可靠语言判定，严格保留这142条 `und`；不可一键设为中文或英文。若以后独立改善原文识别器，应在DEV逐条确认证据后走明确批准的历史元数据更新，不能在同步时猜测。
- 受保护执行器 [`identity-center`](https://github.com/119shenhao/identity-center/blob/main/docs/GAMBLING_CONTENT_SYNC_EXECUTOR.md) 和 ChatGPT 每12小时自动同步任务均使用固定 SHA `09df153ce9fdc57b435adf92b2aceeea393f3678`，不新建 GitHub cron、不重复同步已有回执的帖子。


## 2026-11-22 原文语言同步修复正式收尾：DEV 和 PROD 最终验收

**本节为最新结论，覆盖上文“尚未验收”“固定旧版 SHA”“历史 und 待修复”的旧快照；只针对戒赌论坛。** 正式详细验收已记录于 `main/docs/PROJECT_STATUS.md` 同名结项段落。

- 采集时在 DEV 保存原文语言及验证记录；生产只核对版本/标签/方法并复制，不重新识别、不悄悄降级为 `und`。受保护执行器与每12小时自动任务固定已验证 `09df153ce9fdc57b435adf92b2aceeea393f3678`，原排程未更改。
- [新版同步真实执行 #45026829285](https://github.com/119shenhao/identity-center/actions/runs/45026829285)：新增 2 篇、5 回复、2 回执，复查 `examined=0`；用户已查看两边帖子/回复一致。
- [生产在线验收 #45027269679](https://github.com/119shenhao/gambling/actions/runs/45027269679)：生产 Worker 版本 `0.5.1-language-proof-atomic.20261122`，D1 ready，V2EX `zh-CN`，Google SSO/Azure 仍正常。
- [历史语言元数据修复 #45024860737](https://github.com/119shenhao/identity-center/actions/runs/45024860737)：6篇主帖+857回复修复并回读。
- [最终只读核验 #45026992693](https://github.com/119shenhao/identity-center/actions/runs/45026992693)：剩余142条评论在 DEV 和 PROD 都是 `und`，`dev_source_missing=0`、`dev_source_nonund_unverified=0`，并非同步丢失原文语言。按准确性原则保留原始未知标记，不得批量猜测；人工确认属于可选内容治理工作，不再视为此同步故障遗留。
- 结论：本次用户要求的生产发布、未来同步用新实现、历史错误修复与远端验收均已完成；后续新增来源仍须经过相同严格语言证据检查。不得触碰 `spine-community`。
