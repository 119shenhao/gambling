# 戒赌社区 / Gambling Stories

生产域名：`gambling.nbn369.com`。新仓库为 `119shenhao/gambling`，开发分支 `dev`。仓库地址：https://github.com/119shenhao/gambling 。

从 `119shenhao/spine-community/main` 移植通用论坛框架：帖子、回复、用户互动、后台、多语言、搜索、可选翻译及 SEO。**不复制真实业务数据**。

简体中文叫「戒赌社区」，繁体中文叫「戒賭社區」，提倡戒赌；除简繁中文外的语言遵循英文 **Gambling Stories** 客观中立定位。英文口号：**Real Stories. Real Impacts. Open Discussion.** 所有语言共享同一个社区。

## 本地运行

需要 Node.js 22.13+：
```bash
npm ci
npm run db:local
npm run dev
```
本地 Wrangler D1 独立储存。用 `npm run verify` 进行静态检查与初步测试。

**当前状态（2026-11-21）**：开发和生产两套独立 Cloudflare Worker 环境、D1、统一身份认证客户端已上线；生产 Google 登录已启用，自动化在线跳转验收通过。生产唯一管理员已关联到正式 Identity Center 中已验证的 Owner；真实 Google 浏览器登录仍需本人体验确认。两站不共享 D1/客户端密钥/用户内容；采集与生产 Azure 自动翻译继续关闭。

开发入口：[docs/START_HERE.md](docs/START_HERE.md)，需求：[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)，进度：[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。

- 开发预览入口（用户确认）：https://dev-gambling-community.119shenhao.workers.dev/
- 生产域名入口（用户确认）：https://gambling.nbn369.com/（生产 SSO 自动验收已通过）
