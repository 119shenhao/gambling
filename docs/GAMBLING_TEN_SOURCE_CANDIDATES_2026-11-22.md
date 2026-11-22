# 戒赌社区 10 个独立候选采集来源（8 英文 + 2 中文）
更新：2026-11-22（北京时间）；仅为来源查找与网页结构初筛。**总名单 10 个 ≠ 已接通 10 个**。

## 数量和现状
- 现有正式接入、DEV 真实入库成功：**2 个英文来源**：GamCare、MoneySavingExpert。
- 此次另找到：**6 个英文候选、2 个中文候选**；均尚未完成 GitHub Runner 全文/回复/分页解析、DEV D1 导入及回读，因此**不打开它们的 approved/parser_verified/reuse_allowed 开关**。
- 同一网站上的多个板块算一个来源。所有采集仅写 Gambling DEV，不碰生产。
- 当前 ChatGPT 戒赌论坛自动采集仍每 **6 小时** 一次，每个已接通来源每轮最多新增 **2 篇**。**没有**更改 schedule、已在用的 GamCare/MSE 配置或 GitHub Actions。
- 全部 10 个来源日后若逐一通过验收、每轮又都有足够新帖，理论上每轮最多 20 篇，**并不保证**真有 20 篇或任何新来源现在可自动采集。

## 英文来源（8 个，包含已接通 2 个）

| # | 网站 | 主题与回复依据 | 当前状态和障碍 |
|---|---|---|---|
| EN-1 | **GamCare Forum** https://community.gamcare.org.uk/forum/recovery-diaries/ | 戒赌康复日记；真实跨页和长回复已通过 GitHub Actions DEV 回读 | **现有启用**，已验证 |
| EN-2 | **MoneySavingExpert Forum** https://forums.moneysavingexpert.com/categories/debt-free-diaries | 戒赌负债/康复帖子；曾实测原站 632 回复，保留前 500，另有 67 条回复全入库（2 条待审核） | **现有启用**；站内搜索 HTTP 403，采用已验证种子+栏目扫描，仍需扩展持续发现能力 |
| EN-3 | **PsychForums — Gambling Addiction** https://www.psychforums.com/gambling-addiction-forum-f204/ | 专门戒赌论坛，帖子列表显示回复数，存在多页讨论，例如 https://www.psychforums.com/gambling-addiction/topic108461-50.html | **待接入**；先前 GitHub Runner 访问超时，需解决可达性、逐页原文和回复结构 |
| EN-4 | **Reddit — r/problemgambling** https://www.reddit.com/r/problemgambling/ | 真实戒赌经历及回复，样本 https://www.reddit.com/r/problemgambling/comments/1ubyh80/i_relapsed_and_i_dont_know_what_to_do_anymore/ | **待接入**；Data API/评论树分页、速率/访问约束及内容处理资格未在本项目验收。另一 subreddit 不另算站点 |
| EN-5 | **SoberRecovery Forum** https://www.soberrecovery.com/forums/ | 综合成瘾互助论坛，含具体赌博支持主题 https://www.soberrecovery.com/forums/newcomers-recovery/156124-gambling.html；论坛帖子及多页链接公开 | **待接入**；需筛出赌博主题、验证稳定列表入口/完整分页及来源准入 |
| EN-6 | **Mental Health Forum** https://www.mentalhealthforum.net/forum/ | 真实戒赌困境主题 https://www.mentalhealthforum.net/forum/threads/why-is-it-so-difficult-to-quit-gambling-rather-than-smoking-or-drinking.460425/ | **待接入**；网页检索可找到讨论，但本轮网页打开返回 403；需 Runner 实测及搜集入口 |
| EN-7 | **Beyond Blue Forums** https://forums.beyondblue.org.au/ | 澳大利亚心理支持论坛含赌博成瘾帖子 https://forums.beyondblue.org.au/t5/relationship-and-family-issues/gambling-addiction/td-p/611255 | **待接入**；检索可找到有回复的主题，但网页打开时 403，Runner 仍未验证 |
| EN-8 | **Digital Spy Forum** https://forums.digitalspy.com/ | 综合讨论站，真实完整主帖及回帖样本 https://forums.digitalspy.com/discussion/403133/has-anyone-here-ever-had-a-gambling-problem；帖子 HTML 中有逐条评论及稳定 /discussion/ 数字 ID | **待接入**；赌博相关帖子稀疏、部分陈旧；需安全筛选相关性、列表发现与分页 |

## 中文来源（2 个，均未启用）

| # | 网站 | 主题与回复依据 | 当前状态和障碍 |
|---|---|---|---|
| ZH-1 | **豆瓣 — 戒赌小分队** https://www.douban.com/group/586083/ | 专门戒赌小组；索引页面列出 82、112、278、372 条回复的真实戒赌打卡/上岸主题；组规明确反对博彩代理广告 | **优先候选**；已有网页可见主题与回复数，需 GitHub Runner 完整解析、评论分页/楼中楼关系核实、权限/个人信息与诱赌内容筛选 |
| ZH-2 | **V2EX** https://www.v2ex.com/tag/%E8%B5%8C%E5%8D%9A | 公开话题样本 https://www.v2ex.com/t/1121755?p=1 明确显示 **251 replies** 和 1/2/3 页；另一话题 https://v2ex.com/t/1018492?p=1 显示 **127 replies** | **优先候选**；网页证据明确，需关键词匹配区分真正戒赌/负债与普通理财或投机话题，并验证全文、跨页和回复去重 |

## 明确放弃作为本轮前 10 的来源
- https://www.jieduflarum.com/t/qdb 页面底部出现“专注博彩引流”推广，不宜直接当作安全戒赌来源。
- https://jiedushequ.org/ 首页直接混入赌场注册、送彩金等博彩推广内容；未经严格排除不能自动采集。
- https://gamblingrecoveryhub.org/forums/forum/gambling-journals/ 论坛当前公开显示仅 1 个主题，无法维持每轮 2 篇。
- https://gamblingtherapy.org/forum/ 及 https://community.gamblinghelponline.org.au/ 可作为后备：前者既往采集环境 HTTP 403，后者此前 HTML 为动态外壳、未发现完整回复；不冒充可用来源。

## 正式接入顺序与技术验收
建议顺序：中文 **V2EX → 豆瓣戒赌小分队**；英文优先 **SoberRecovery → Digital Spy**（网页可读），其后为 **PsychForums → Reddit → Mental Health Forum → Beyond Blue**（需先处理运行环境/接口可达性）。根据采集密度和可访问性可再调整优先级。

每个新来源必须依次通过：真实 GitHub Runner 可达性 → 自动发现新帖及原站稳定 source_id → HTML/API 标题和完整原文 → 所有分页和评论/有证据的楼中楼 → 去引用/避免重复和虚构父子关系 → 敏感数据及博彩营销过滤 → 来源使用范围核验 → DEV exclusions、claim、最多500条前缀严格保存和 501 起不存、complete 或 long/start/append/finish → 独立开发 D1 回读（公开+待审核状态严格核对）→ 再将其追加到 `scripts/gambling_sources.json`，使既有 `sites=['all']` 的**原有** 6 小时任务自动纳入。

**本轮只是网页调查和永久记录，不是新站点的 Runner 解析/开发库入库通过记录；没有新开定时器，也没有改变原有采集任务的运行频率。**

## 2026-11-22 中文接入第一阶段开发（更新记录）

- **已提交** `scripts/gambling_chinese_source_probe.py`：针对 V2EX 3 页真实帖子、赌博标签列表和豆瓣戒赌小组公共页面的只读 HTML 结构探测，只输出节点数量、回复数/分页等聚合元数据，不打印用户正文或身份。
- **已提交** `scripts/gambling_v2ex.py` 独立严格解析器、`tests/test_gambling_v2ex.py`（7 项合成契约测试）、`scripts/gambling_v2ex_live_probe.py`（真实 251 回复主题的内存解析检查）；现有 `gambling_forums.py` 已接入 V2EX 的 ID、自动发现、分页适配分支；`gambling_collect.py` 预留了其长帖分批路径。
- 将 `v2ex` 与 `douban` 写入 `scripts/gambling_sources.json`，**均为 approved=false / parser_verified=false / reuse_allowed=false**；现有 GamCare 和 MSE 两个来源保持启用，不会将中文来源提前导入 DEV 或生产。
- **已使用现有** `.github/workflows/gambling-source-probe.yml` 只读工作流，向 `.github/gambling-source-probe-request.json` 写入新的触发请求 `probe-20261122-v2ex-douban-parser-v02`，提交 SHA `90b2f6a072877245312c642a9f805dd63b6a30a6`。
- **验收未完成**：当前 GitHub 连接器可写入仓库及读取指定运行 ID 的日志，但无法列出刚触发的工作流运行 ID，因此这次 Runner 的测试结论仍须回读确认。离线测试代码提交不等于已经在 GitHub Runner 通过；真实 251 回复的完整解析和 500 封顶仍待读取实际新日志。
- 豆瓣公共页面可能无法匿名读取，禁止通过登录绕过访问限制。只有真实 Runner、严格完整解析、来源使用资格及 DEV D1 回读全部满足，才可开启这两个新来源。
- **任务频率保持每 6 小时一次**，每来源每轮上限 2 篇；无新增 GitHub Actions 定时触发器，生产环境未改变。

