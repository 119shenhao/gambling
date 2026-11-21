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
