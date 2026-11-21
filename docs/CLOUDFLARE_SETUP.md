# Gambling Community — Cloudflare 部署及资源隔离

更新时间：2026-11-21；以实际 API 与 Preview 线上验收为准。

## 已确认的资源名

| 类型 | 开发 Preview | 正式 Production |
|---|---|---|
| Worker | 同一个 `gambling-community`，分支 `dev` | 同一个 `gambling-community`，分支 `main` |
| D1 | `gambling-community-dev`（UUID 待核对） | `gambling-community-prod`（UUID 待核对） |
| R2 | `gambling-community-public-dev` | `gambling-community-public-prod` |
| Issuer | `https://dev-identity-center.119shenhao.workers.dev` | `https://idcenter.nbn369.com` |
| Site | Cloudflare dev Preview 的实际 URL 待核对 | `https://gambling.nbn369.com`（计划域名） |

用户表示上述 Cloudflare 资源已创建，**并不代表已通过在线授权读回验证**。切记旧 Spine 的 UUID 和 CDN 域名不能移植。

## 现在的安全状态

`dev/wrangler.jsonc` 已添加独立 Preview/Production R2 绑定；两套环境的公开 R2 JSON、自动翻译、Google 登录、内容采集与导入均处于关闭状态。

暂未添加 D1 远程绑定：Wrangler 必须使用 Cloudflare 详情页显示的 **真实 UUID**，不能凭名称或猜测绑定。为了不把 Preview 错绑生产库，缺 UUID 就不进行远程迁移。本站 `main` 目前仍只包含项目说明，不能当作已可发布的生产源码。

## 从 Cloudflare 读取 D1 UUID

Cloudflare Dashboard → Workers & Pages → D1 SQL Database（也可能显示 Storage & databases → D1）→ 逐个打开 `gambling-community-dev` 和 `gambling-community-prod` 的详情，在 Database ID / UUID 字段复制各自的 UUID。**只需要这两个 UUID，不要在聊天中发送 Cloudflare API Token、Secrets、Google Client Secret 或 Cookie。**

## 下一步由代码和自动化完成

1. 将开发 UUID 写入 `wrangler.jsonc → previews.d1_databases[]`，绑定 `DB`；将生产 UUID 写入根级 `d1_databases[]`，绑定 `DB`，必须核对名称、UUID、环境一致。
2. 新增独立迁移配置 `wrangler.preview-migrations.jsonc`，绑定 `PREVIEW_DB`，固定开发 D1 名称与 UUID；部署准备程序仅在 Cloudflare **dev Preview 构建**且 GitHub 分支为 `dev` 时可以运行 `migrations/v1`。无环境或 UUID 不匹配时拒绝；绝不连接正式 D1。
3. 在 Cloudflare Worker Builds 中核对 GitHub 仓库 `119shenhao/gambing`、Production branch=`main`、Preview builds=on、Preview command=`npx wrangler preview`、Deploy command=`npx wrangler deploy`、Build command 留空、根目录 `/`。启用稳定 dev Preview URL。
4. 开发 Preview 部署后的 `/api/health` 必须返回 `status=ok` / `databaseReady=true`，实际论坛页面、公开帖子和登录前访问也要运行测试；如返回 503，先排查 Preview D1 绑定与迁移。
5. Identity Center 开发环境先注册 disabled 的 `gambling-community-dev`、精确 HTTPS 回调为实际 Preview URL + `/api/auth/identity/callback`，配置专属服务器端 Secret 并验证后启用；不再设置网站自己的直连 Google 回调。
6. 开发真实验收成功之后，另行批准生产迁移、配置 `gambling-community-prod` 和 `gambling.nbn369.com`。R2 公开 JSON 回填与 CDN 可后置开启。

## 回滚与限制

- 登录失败：保持 `IDENTITY_LOGIN_ENABLED=false`，不切换回论坛独立 Google 登录。
- 预览迁移失败：停止部署，核对固定开发 UUID，严禁改写生产 D1 以使构建成功。
- R2/CDN 未就绪：保持 `PUBLIC_CONTENT_ENABLED=false`、`PUBLIC_CONTENT_READS=false`，使用数据库原接口。
- 生产发布/生产 D1 写入/域名路由更改需要独立验收及授权，不能以复制代码或用户创建资源视为生产上线批准。
