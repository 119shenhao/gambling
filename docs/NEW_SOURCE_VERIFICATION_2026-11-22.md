# 戒赌论坛新增外站来源核验（2026-11-22）

范围：仅 `119shenhao/gambling/dev`，**只读**核验新来源，不修改生产、定时频率或现有 GamCare 采集设置。

## 真实 GitHub Actions 验证

- 工作流：<https://github.com/119shenhao/gambling/actions/runs/44996585546>
- 结果：**Success（探测程序正常执行）**。这并不代表候选站点均通过测试或可以正式采集。
- 技术：`scripts/gambling_source_probe.py` 和按需触发的 `.github/workflows/gambling-source-probe.yml`。仅 GET 公共网页，记录 HTTP 状态、主题链接与评论容器数量、分页信息；不输出帖子正文、不写入 D1。
- 现有采集任务维持每 6 小时，每个启用来源最多采集 2 篇，跨页最多 500 条评论。

| 来源 | 本轮实际返回 | 结论/下一步 |
|---|---|---|
| **PsychForums** Gambling Addiction（https://www.psychforums.com/gambling-addiction-forum-f204/） | GitHub Runner 对列表、单帖、分页帖连续三次超时（network_error）；网页搜索服务可看到约2,315个主题、一篇12条帖子/两页、一篇133帖子/14页及稳定数字ID | 值得保留候选；须先解决 Runner 到站连接，再开发 phpBB 结构的自动发现/正文/分页完整校验；当前不可开启 |
| **MoneySavingExpert Forum** 戒赌康复日记（https://forums.moneysavingexpert.com/discussion/6512900/redemption-the-journey-of-a-recovering-gambling-addict） | 原帖 HTTP 200，约 886KB HTML，探测到32个候选正文容器；第49页 HTTP 200，约889KB，探测到29个候选正文容器（**只是选择器匹配数量，非已核对回复数**） | HTTP 和多页结构可访问；需要单独 Vanilla 论坛解析器、排除引言/签名、总回复计数核对。站点条款保留用户内容版权，尚无明确全文再发布许可，不能开启自动导入 |
| **Gambling Help Online** 新社区（https://community.gamblinghelponline.org.au/s/） | HTTP 200，但 0 个可解析帖子链接、0 个可解析评论正文；动态 Salesforce 社区外壳 | 目前不能自动提取完整主题与回帖；不绕过限制 |
| **Evive Community**（https://community.getevive.app/） | HTTP 403 | 不可用；原 GamTalk 已迁至 Evive，不将旧域名误认独立来源 |
| **Gambling Therapy**（https://gamblingtherapy.org/forum/） | 先前实际采集环境 HTTP 403 | 继续关闭 |
| **Reddit** r/problemgambling / r/GamblingAddiction | 有公开讨论，但未验收项目的外部 Data API 与内容再利用条件，未实测完整评论树 | 不作为已接通来源 |

### 权限与技术门槛

每个外站独立通过以下门槛后，才改动 `scripts/gambling_sources.json` 开启：原站稳定 ID、公开候选列表、真实主帖与回帖解析、实际分页读取、最多 500 条与 501 起截断、去重、隐私筛选、开发 D1 完整回读，以及明确适用的内容使用许可。不能把 HTTP 200 或评论容器数量误当作完整入库能力。

当前 **正式可用仍仅 GamCare** 的 New Members Intros 和 Recovery Diaries 两个栏目；本次没有启用任何新数据源，没有运行新增全文导入。下一步优先验证 PsychForums Runner 访问问题和 MoneySavingExpert 的解析结构/使用范围，在明确可用后再加入原有定时采集配置，不新建定时器。

### 外部核对资料

- PsychForums 列表：<https://www.psychforums.com/gambling-addiction-forum-f204/>
- PsychForums 两页样本：<https://www.psychforums.com/gambling-addiction/topic126528.html>
- PsychForums 多页样本：<https://www.psychforums.com/gambling-addiction/topic108461-50.html>
- MoneySavingExpert 条款：<https://www.moneysavingexpert.com/site/terms-conditions/>
- Gambling Help Online 社区条款：<https://www.gamblinghelponline.org.au/terms-conditions>
- GamTalk → Evive 迁移说明：<https://www.getevive.com/gamtalk>
