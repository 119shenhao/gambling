# Gambling Community — Cloudflare 部署及资源隔离

更新时间：2026-11-21；以实际 API 与 Preview 线上验收为准。

## 已确认的资源名

| 类型 | 开发 Preview | 正式 Production |
|---|---|---|
| Worker | 同一个 `gambling-community`，分支 `dev` | 同一个 `gambling-community`，分支 `main` |
| D1 | `gambling-community-dev`（UUID 已从用户截图确认） | `gambling-community-prod`（UUID 已从用户截图确认） |
| R2 | `gambling-community-public-dev` | `gambling-community-public-prod` |
| Issuer | `https://dev-identity-center.119shenhao.workers.dev` | `https://idcenter.nbn369.com` |
| Site | `https://dev-gambling-community.119shenhao.workers.dev`（用户提供；线上状态待检测） | `https://gambling.nbn369.com`（用户确认生产访问地址；上线状态待核验） |

用户表示上述 Cloudflare 资源已创建，**并不代表已通过在线授权读回验证**。切记旧 Spine 的 UUID 和 CDN 域名不能移植。

## 现在的安全状态

`dev/wrangler.jsonc` 已添加独立 Preview/Production R2 绑定；两套环境的公开 R2 JSON、自动翻译、Google 登录、内容采集与导入均处于关闭状态。

已将用户从 Cloudflare 数据库页面提供的 **真实 UUID** 加入 Wrangler 开发/生产绑定。开发 UUID `a92cf620-2a0b-46e1-a0ff-2e0c94218f37`，生产 UUID `7bba9ada-589f-493b-8fcf-60265fc0efac`。这仅表示代码配置，不代表远程数据库已迁移或上线。本站 `main` 目前仍只包含项目说明，不能当作已可发布的生产源码。

## Cloudflare D1 UUID 已核对

已通过用户提供的 Cloudflare D1 详情页截图确认：`gambling-community-dev = a92cf620-2a0b-46e1-a0ff-2e0c94218f37`；`gambling-community-prod = 7bba9ada-589f-493b-8fcf-60265fc0efac`。不需要再索取 UUID，也不需要用户发送 API Token / Secret。

## 下一步由代码和自动化完成

1. **已完成**：开发 UUID 写入 `wrangler.jsonc → previews.d1_databases[]` 的 `DB`；生产 UUID 写入根级 `d1_databases[]` 的 `DB`，并校验名称、UUID、环境各自唯一。
2. **已完成**：独立迁移配置 `wrangler.preview-migrations.jsonc`，绑定 `PREVIEW_DB`，固定开发 D1 名称与 UUID；部署准备程序仅在 Cloudflare **dev Preview 构建**且 GitHub 分支为 `dev` 时可以运行 `migrations/v1`。无环境或 UUID 不匹配时拒绝；绝不连接正式 D1。
3. 在 Cloudflare Worker Builds 中核对 GitHub 仓库 `119shenhao/gambling`、Production branch=`main`、Preview builds=on、Preview command=`npx wrangler preview`、Deploy command=`npx wrangler deploy`、Build command 留空、根目录 `/`。启用稳定 dev Preview URL。
4. 开发 Preview 部署后的 `/api/health` 必须返回 `status=ok` / `databaseReady=true`，实际论坛页面、公开帖子和登录前访问也要运行测试；如返回 503，先排查 Preview D1 绑定与迁移。
5. Identity Center 开发环境先注册 disabled 的 `gambling-community-dev`、精确 HTTPS 回调为实际 Preview URL + `/api/auth/identity/callback`，配置专属服务器端 Secret 并验证后启用；不再设置网站自己的直连 Google 回调。
6. 开发真实验收成功之后，另行批准生产迁移、配置 `gambling-community-prod` 和 `gambling.nbn369.com`。R2 公开 JSON 回填与 CDN 可后置开启。

## 回滚与限制

- 登录失败：保持 `IDENTITY_LOGIN_ENABLED=false`，不切换回论坛独立 Google 登录。
- 预览迁移失败：停止部署，核对固定开发 UUID，严禁改写生产 D1 以使构建成功。
- R2/CDN 未就绪：保持 `PUBLIC_CONTENT_ENABLED=false`、`PUBLIC_CONTENT_READS=false`，使用数据库原接口。
- 生产发布/生产 D1 写入/域名路由更改需要独立验收及授权，不能以复制代码或用户创建资源视为生产上线批准。

## 预览 D1 自动迁移（UUID 已确认，等待 Cloudflare Preview 运行与在线验收）

已实现 `scripts/preview-migrate.mjs`，由 `scripts/prepare-build.mjs` 在构建时调用。本地/GitHub CI/main 生产都不运行远端 SQL。只在 Cloudflare 的 `WORKERS_CI=1` 且 `WORKERS_CI_BRANCH=dev` 并且存在 `wrangler.preview-migrations.jsonc` 时，先确认 `gambling-community-dev` UUID、预览配置、R2 名称、与生产/源项目数据库隔离，再运行 Wrangler 的版本化 D1 迁移并验证 schema_version。缺少环境标识则安全跳过；在标识完整且配置不匹配时中止构建。只有 Cloudflare Preview 远程迁移成功并实际 /api/health 检查通过才可判定“数据库已准备好”。

下一步收到两个真实 UUID 后，写入绑定并触发正常 `dev` 提交，由 Cloudflare Preview Build 自动执行；随后使用 `/api/health` 和迁移日志确认。若 Cloudflare 的 Build Token 缺少 D1 权限，会停止部署，届时需要受控 GitHub Actions Secret 配置，**不要在聊天里提交 Token 明文**。

## GitHub 仓库更名后的 Cloudflare 构建核对

GitHub 仓库规范地址已更正为 `https://github.com/119shenhao/gambling`，Cloudflare 的 Worker / D1 / R2 **不改名**。

Cloudflare Dashboard → Workers & Pages → `gambling-community` → Settings → Builds / Git integration：确认已关联 `119shenhao/gambling`，正式分支仍是 `main`、预览分支仍是 `dev`，并检查更名后的首次 Preview 构建日志。若 GitHub 原地址重定向仍可用，也不能据此断言 Cloudflare webhook/build 一定正常；必须观察实际构建事件与预览部署。

## 源论坛 URL 与域名检查

源码已经替换所有旧站的 Spine Worker 域名、公开 JSON 域名和投影 Header。规划的 CDN Host 为 `gambling-data-dev.nbn369.com` 与 `gambling-data.nbn369.com`，**尚未开启**公开 R2 JSON。Cloudflare Preview 真实 URL 未获验证，故禁止硬编码猜测 URL，未来仅在真实验证后设置开发变量 `PUBLIC_CONTENT_ORIGIN`。确认生产/开发的独立 D1 UUID 和 R2 bucket 均保持正确，不因 GitHub 更名改变。

## Identity Center 下一阶段准备

Wrangler 已设置公开配置：Preview `IDENTITY_ISSUER=https://dev-identity-center.119shenhao.workers.dev`, `IDENTITY_CLIENT_ID=gambling-community-dev`；Production `IDENTITY_ISSUER=https://idcenter.nbn369.com`, `IDENTITY_CLIENT_ID=gambling-community-prod`。`IDENTITY_LOGIN_ENABLED` 均为 false，尚未设置 `IDENTITY_REDIRECT_URI` 和 `IDENTITY_CLIENT_SECRET`，因为尚无已验收的真实 Preview URL 与客户端注册记录。

确认 Preview URL 后按 `119shenhao/identity-center/docs/NEW_APP_INTEGRATION_GUIDE.md` 在开发中心以 disabled 状态注册精确回调，随后由服务器端受控配置一次性机密 Secret，验证后启用。**生产注册及启用不属于开发部署授权**。

## 已明确的站点 URL（2026-11-21）

用户确认开发 URL：`https://dev-gambling-community.119shenhao.workers.dev/`；正式 URL：`https://gambling.nbn369.com/`。开发、生产 OAuth 回调分别配置为 `https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback` 与 `https://gambling.nbn369.com/api/auth/identity/callback`。这些 URI 只用于**准备白名单**；尚未在 Identity Center 注册客户端，也没有启用登录和 Secret。

`dev/.github/workflows/dev-online-smoke.yml` 在开发提交后从 GitHub Actions 的外网执行**只读** HTTP 检查：开发 `/api/health` 必须返回 Preview + D1 Ready、首页包含正确品牌、`robots.txt` 禁止抓取、旧 Google 直接登录返回 410。此流程不能代替 Cloudflare 构建日志、用户登录实测或生产验收；如果失败，先核对 Cloudflare Git 关联与 D1 迁移，不得改写生产库。

## 开发站线上与身份中心登记核验

实际开发论坛：`https://dev-gambling-community.119shenhao.workers.dev/`，生产入口：`https://gambling.nbn369.com/`。生产当前是否部署可用并未验收。

GitHub 只读在线验收：[#44883988827](https://github.com/119shenhao/gambling/actions/runs/44883988827)；开发 D1 Ready、HTTP 200、禁止索引、旧直连登录 410 均通过。

开发 Identity Center 客户端已注册 Disabled：[#44884259846](https://github.com/119shenhao/identity-center/actions/runs/44884259846)。准确回调 `https://dev-gambling-community.119shenhao.workers.dev/api/auth/identity/callback`；不共享原站认证密钥；`IDENTITY_CLIENT_SECRET` 尚未设置。先完成密钥安全注入、中心匹配摘要、开发激活和线上 OAuth 真实测试，登录开关才允许更改。已设置 `global_fetch_strictly_public`，沿用 Spine 实测的跨 Worker 请求兼容方案。

## 独立开发 OAuth Secret 引导（待 CI 与 Cloudflare Build 运行）

基于 Spine 2026-11-20 已验收的 `wrangler preview secret put` 方案，新增 `scripts/provision-dev-identity.mjs`：仅为 `gambling-community` 的命名预览 `dev` 写入 `IDENTITY_CLIENT_SECRET`，而不是对普通生产 Worker 进行 `secret put`。仅以 `wrangler.identity-dev-provision.jsonc` 访问 `identity-center-dev`（固定 UUID），从新论坛开发 D1 读取已验证的授权迁移及收据；中心应用需保持 disabled。Secret 明文只入 Cloudflare 预览 Worker，中心 D1 存 SHA-256 Base64URL 校验摘要。所有代码和 SQL 操作必须先经 CI，运行一次后拆除构建调用。

## 2026-11-21 DEV SSO Secret 与客户端激活验证

- DEV 论坛 Cloudflare Preview Build 安全运行一次性 Secret bootstrap。独立随机 Secret 原文仅写入预览 Worker，两个开发 D1 只存 SHA-256 Base64URL 摘要；[身份中心只读验收 #44885090134](https://github.com/119shenhao/identity-center/actions/runs/44885090134) 检查了唯一有效摘要和禁用状态，结果成功。
- 已从 `scripts/prepare-build.mjs` 移除一次性 bootstrap 的自动调用，后续普通构建不会再次生成或轮换 Secret；保留脚本但不自动执行。
- [Identity Center DEV 客户端激活 #44885210412](https://github.com/119shenhao/identity-center/actions/runs/44885210412) 成功：`gambling-community-dev` 已启用，有效摘要唯一、回调唯一且精确匹配。未动生产认证中心/论坛数据。
- 将 `dev/wrangler.jsonc → previews.vars.IDENTITY_LOGIN_ENABLED` 开启，仅开发 Preview，正式站仍关闭。通过新工作流 `dev-oauth-smoke.yml` 在线验证 `/api/me`、授权码登录重定向和 PKCE、无状态回调拒绝、旧 Google 直连 410；**真人 Google 回跳尚待用户验收**。

## 2026-11-21 跳过 Identity Center 的提供商选择页（仅开发）

用户实际完成 Google 登录，但要求戒赌社区点击登录后不再显示 Identity Center 的中间选择页。认证中心 DEV 已支持 `gambling-community-dev` 专用、严格约束客户端+Issuer+回调的 `provider_hint=google`；保留中心 SSO 复用、PKCE、Nonce、State、一次性授权码及后端验签和会话处理。认证中心线上真实跳转 [#44886399265](https://github.com/119shenhao/identity-center/actions/runs/44886399265) 成功，未提示时原选择页不变。

本次新论坛 DEV `src/auth.ts` 仅在精确开发配置下传 `provider_hint=google`，不直接访问 Google OAuth，也不修改正式站。`dev-oauth-smoke.yml` 更新为验证论坛 → 身份中心 → Google 两次 HTTP 302 及证明 Cookie，全程不跟随到 Google 页面，不记录敏感查询参数。**仍需用户实际浏览器验收**。

## 共享 Azure F0 翻译准备：开发专用

目前新论坛 DEV 的 `TRANSLATION_ENABLED=true` 只表示允许服务端按需启用；**不会自动生成翻译**，因为 D1 `settings.translation_enabled=false` 且新的 DEV Preview Worker 尚无 `TRANSLATOR_KEY`。Azure 密钥只允许以 Cloudflare Preview Worker Secret 保存，不允许放在 GitHub、聊天、D1 或前端。

如果有权限配置本地 Wrangler CLI，可在已授权 Cloudflare 账户执行：

```sh
npx wrangler preview secret put TRANSLATOR_KEY --worker-name gambling-community --name dev
```

输入同一 Azure F0 资源的密钥时不要在终端命令参数里写明文。普通 `wrangler secret put` 面向正式 Worker 的操作，**不能替代**以上 Preview 方式。地区由 DEV Wrangler vars 设置为 `eastus`，账户免费 F0 核验记录有效期限为31天，过期前必须重新核实真实 Azure 配额和计划；不要自动刷新时间。配置后检查 `/api/health` 的 Preview `translationSetup.keyConfigured` 与 `freeTierVerified`，再由本站管理员在翻译服务管理中启用本论坛 D1 `translation_enabled`，进行真实多语言测试。

## 2026-11-21 Cloudflare Preview Secret 丢失问题已定位（待用户重新绑定）

- 第一次 [DEV 真实 Azure 自动测试 #44889928443](https://github.com/119shenhao/gambling/actions/runs/44889928443) 返回 HTTP 503；D1 诊断 `azure_dev_smoke_20261121=not_started`、预算 0，**没有调用 Azure 产生字符费用**。
- [DEV Secret 验证 #44889584465](https://github.com/119shenhao/gambling/actions/runs/44889584465) 曾显示 `keyConfigured=true`；随后多个 DEV Cloudflare Preview 构建后，新版本返回 `keyConfigured=false`、`azureConfigurationReady=false`。[只读诊断日志 #44890037912](https://github.com/119shenhao/gambling/actions/runs/44890037912) 留存了对比。这说明 DEV 命名 Preview 的运行时已失去 Secret 绑定，**不是 Azure Key 已被证明无效**。
- Cloudflare 资料说明 Preview Base Secret 变更不会同步到已创建的命名 Preview；确实也存在历史上 Preview 重新部署后丢失 Secret 的已修复 SDK 缺陷（[Cloudflare 问题 #15942](https://github.com/cloudflare/workers-sdk/issues/15942)）。当前仓库 package-lock Wrangler 是 `4.158.0`，晚于修复版，因此不能仅据此认定遇到了同一个老 bug。需在最终代码部署后将 `TRANSLATOR_KEY` **绑定到已存在的 `dev` 命名 Preview 的最新部署**，不要只填写 Preview Base。Secret 明文不可读取或从 Prod 自动复制。
- 现在把 DEV 一次性实测路径改为：只有同一 Secret 完成英→中和中→英两次真实成功，才通过一个 D1 batch 设置 active provider Azure、每日5000、每月10000与 `settings.translation_enabled=true`，失败保持关闭。随后回归验证预算和页面译文缓存；生产开关保持关闭，待论坛正式版验收。
