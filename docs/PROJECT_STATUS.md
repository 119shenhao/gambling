# 项目状态 — Gambling Community

- 2026-11-21 新建空仓库 `119shenhao/gambing`，main 仅有项目入口，dev 进行源码移植。
- 采用 `spine-community/main` 通用代码，并改造产品命名、分类、SEO 域名、统一身份登录新用户映射。
- 所有原站 D1/R2、Google OAuth、采集/同步生产任务均未迁入；新站仅能本地使用独立 D1。公开站点及生产 OAuth 尚未配置。
- 尚需：CI 与本地 D1 验收、领域旧字段全面清理、隐私与社区规则、完整多语言校对、创建预览 D1、注册 Identity Center 开发客户端、真实 Google SSO 双论坛场景、内容安全与生产部署审批。
- 本阶段复制代码并非宣称新站已正式发布。

## 2026-11-21 初次源码移植验收

- 开发分支提交：`a2b33624bc74813c280bddeccff8ac3a3fc10d7a`，共 80 个文件。
- [GitHub Actions 首轮 CI #44881408456](https://github.com/119shenhao/gambing/actions/runs/44881408456)：**成功**。`npm ci`、`npm run verify`（TypeScript + 产品隔离/品牌自动检查）、`npm run db:local`（全部独立本地 D1 迁移）、`npm run build`（前端版本化构建）全部完成。
- 此结果证明源码可以在 CI 中通过检查与本地迁移，**不证明浏览器端所有业务交互、真实 Google/Identity Center 登录、Cloudflare 预览或生产已经可用**。
- 不复制原站已验证的 Google 域名证明页面、Cloudflare D1/R2 绑定、远端采集/同步 Actions；原数据没有导入。
- 技术债：仍存在源项目兼容字段（如 `body_part` / `symptom_duration_days`），其业务 UI 已初步隐藏/简化；应逐步清理并完成真实端到端回归。源项目大规模医疗业务测试不能直接当作新站验收。
