# 戒赌社区 / Problem Gambling

计划域名：`gambling.nbn369.com`。新仓库为 `119shenhao/gambing`（保持用户已创建的拼写），开发分支 `dev`。

从 `119shenhao/spine-community/main` 移植通用论坛框架：帖子、回复、用户互动、后台、多语言、搜索、可选翻译及 SEO。**不复制真实业务数据**。

简体中文叫「戒赌社区」，繁体中文叫「戒賭社區」，提倡戒赌；除简繁中文外的语言遵循英文 **Problem Gambling** 客观中立定位。英文口号：**Real Stories. Real Impacts. Open Discussion.** 所有语言共享同一个社区。

## 本地运行

需要 Node.js 22.13+：
```bash
npm ci
npm run db:local
npm run dev
```
本地 Wrangler D1 独立储存。用 `npm run verify` 进行静态检查与初步测试。

**当前仅开发基线**：未创建新 Cloudflare 预览/生产 D1、R2、Google OAuth 或 Identity Center 客户端；未部署、未开放真实登录或内容采集。不要将 Spine 的数据库、密钥、域名、旧授权连接到本项目。

开发入口：[docs/START_HERE.md](docs/START_HERE.md)，需求：[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md)，进度：[docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)。
