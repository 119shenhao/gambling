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
