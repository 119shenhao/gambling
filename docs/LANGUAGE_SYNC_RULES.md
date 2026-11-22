# 戒赌论坛：原文语言一次识别与 DEV→PROD 一致性（2026-11-22）

## 用户确认规则（仅适用于 119shenhao/gambling）

1. **开发环境负责识别**：新采集的主帖、每条回帖及楼中楼分别执行一次 `tinyld-heavy` 独立语言判断；导入器在同一个 D1 事务内写入 `source_lang`、`source_lang_mode` 和对应当前内容版本的 `content_language_verifications`。
   **待审核与屏蔽内容同样在 DEV 内部保存识别凭据**（不代表对外发布）。旧版只对已发布内容写凭据，存在审批后缺记录的风险，已在 DEV 代码中修正；彻底删除的内容不得再附着验证记录。
2. **生产同步不识别**：仅从开发库读取上述语言标记与语言验证记录，核对 `content_id`、`content_version`、`language`、`method`。验证一致，原样复制到生产库。
3. **不允许静默降级**：开发库记录了 `zh-CN`、`zh-TW`、`en`、`ja` 等可识别语言，却缺少当前版本验证记录、方法无效、语言不一致时，返回带内容 ID 的确定性错误；不以 `und` 顶替，也不写生产或开发同步回执。修复开发端后重试。
4. **真未知与显式用户选择**：确实无法识别的 `und` 可以保留，但不能覆盖已确认语言。用户或管理员明确选择的 `source_lang_mode=manual` 是独立的手动决定，不得伪造成 tinyld 自动识别；如存在版本不匹配或与手动选择冲突的验证记录，同样停止同步。
5. **历史内容**：已有同步回执的生产帖不会重新进入一次性同步队列。历史错误的生产语言元数据必须单独审计与修正，不得重导原文、改评论树或覆盖回执。
6. **权限边界**：DEV 修复只能使用戒赌论坛自己的预览 D1。生产写入、受保护执行器代码的提交 SHA 更新及线上验收须走原审批与恢复点流程；不修改 Spine 项目或它的任何任务。

## 源码入口

- `src/source-language.ts`：独立识别器 `tinyld-heavy`（识别由 DEV 执行）。
- `src/collect.ts` 和 `src/import.ts`：普通采集/导入的同批次语言凭据。
- `src/collect-long.ts`：V2EX 等分页长帖的主帖和评论语言凭据，在最后的原子 `finish` 中与正文同批写入。旧版本遗漏，DEV 补丁自 `0335bbc35d` 开始。
- `src/language-state.ts`：`verificationWrite`，确保凭据仅附着于已发布且版本匹配的内容。
- `scripts/sync-preview-to-production.mjs`：无识别模型调用，仅依据开发端数据做严格一致性校验；缺证据或冲突时 fail closed。

## 历史 DEV 数据只读审核与可控修复

脚本 `scripts/repair-preview-language-proofs.mjs` 使用与 Worker 同一个 `src/source-language.ts` 经 esbuild 打包的检测实现，不另造规则，不接受任意数据库路径或 SQL。只扫描 `gambling-community-dev` 中 **published / auto / 非 und** 且缺少当前版本匹配语言凭据的帖子和评论。

- 只读查看：`npm run repair:preview-language -- --limit=100`（需要已有 Cloudflare 预览 D1 访问凭据）。
- 只有复核完成并取得 DEV 写入批准后才可执行：
  `GAMBLING_PREVIEW_LANGUAGE_REPAIR_CONFIRM=a92cf620-2a0b-46e1-a0ff-2e0c94218f37 npm run repair:preview-language -- --limit=100 --apply`。
- 只会对**缺少**验证记录、且重新运行原识别器与已有 `source_lang` **严格一致**的历史内容补写 `tinyld-heavy` 当前版本验证记录；已存在但冲突的凭据、识别结果不同及无法确认的帖子/回复，只出具匿名内部 ID 与原因的复核清单，不自动覆盖。
- 写入后读回所有新凭据；绝不改变标题、正文、评论、回复父子关系、用户、原文语言和同步回执。历史修复是一次性例外，不属于每次生产同步步骤。

## 验收原则

- `npm run verify` 通过；中文、英文、日文和其他语言分别测试准确复制与缺证据拒绝。
- 对历史 V2EX #1121755 / DEV topic `5aae46c6-56d8-468d-8d24-76bc689f09d2`，先只读核对 `topics/comments` 与 `content_language_verifications` 的原始字段；这篇已同步数据需要单独的生产语言元数据修正和后续缓存/SEO 检验。
- 戒赌论坛当前正式同步通道位于 `119shenhao/identity-center`，使用 **固定审核提交** `94dded5100fd3d3ecc1758f9fba13d82be04c694`。本次仅修改 `gambling/dev`，**固定生产执行器不会自动使用新 DEV 代码**；不可把 GitHub 提交等同于生产生效，发布前还需做原有测试、审批、固定提交升级和真实读回验收。
