# COLLECTION API GUIDE — 第三方 AI 帖子导入操作手册

> 仓库：`119shenhao/gambling`；分支：`dev`；更新：2026-11-22。本文仅说明开发环境 API 的操作方法、顺序、参数、异常处理与验收。

## 1. 地址和调用前检查

开发 API 根地址：`https://dev-gambling-community.119shenhao.workers.dev`

生产站 `https://gambling.nbn369.com` **不提供导入/采集写入接口**。所有 POST 请求使用 `Content-Type: application/json`。建议从服务器端 Python/curl 调用；跨域浏览器写入会被拒绝。当前接口没有全局 API Key，但 `complete` 和 `release` 必须携带认领返回的临时 `lease_token`，不要公开它。

**第一步必须检查：**

```bash
curl -fsS 'https://dev-gambling-community.119shenhao.workers.dev/api/health'
```

检查响应中 `environment` 为 `preview`、`importEnabled` 和 `collectEnabled` 都是 `true`。这是**预期条件，不是对当前线上状态的断言**。如果不满足，停止并报告，不要尝试生产接口。

## 2. 推荐接口及顺序

自动采集外部帖子，优先使用 `/api/collect/*`：

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/collect/exclusions?site=reddit&limit=200` | 查询已完成/认领中的来源 ID |
| POST | `/api/collect/claim` | 获取来源 ID 的 6 小时认领租约 |
| POST | `/api/collect/complete` | 原子导入主帖、评论和楼中楼 |
| POST | `/api/collect/release` | 解析失败时释放认领 |
| GET | `/api/collect/queue?site=...` | 可选：读取候选队列 |
| POST | `/api/collect/queue` | 可选：候选检查、入队及状态标记 |

**顺序：**

```text
GET health
 → 发现来源帖子、取得稳定 source_id
 → GET exclusions（如有 next_cursor，循环分页）
 → POST claim（只处理 granted）
 → 获取并校验完整标题、正文、一级评论、楼中楼
 → POST complete
 → 检查响应 + 回读验证
失败 → POST release（若 complete 结果不明，先查询状态）
```

### 2.1 查询排除列表

```bash
curl -fsS 'https://dev-gambling-community.119shenhao.workers.dev/api/collect/exclusions?site=reddit&limit=200'
```

示例响应（示意数据）：

```json
{"site":"reddit","items":[{"source_id":"abc123","status":"completed","lease_expires_at":null}],"next_cursor":null}
```

跳过 `completed` 及仍有效的 `claimed`。若 `next_cursor` 非空，则继续传入 `cursor=<next_cursor>` 直到结束。该查询不替代并发认领。

### 2.2 认领

```bash
curl -sS -X POST 'https://dev-gambling-community.119shenhao.workers.dev/api/collect/claim' \
 -H 'Content-Type: application/json' \
 --data '{"site":"reddit","source_ids":["abc123"],"collector_id":"external_ai_01"}'
```

响应结构示例：

```json
{"site":"reddit","lease_seconds":21600,"results":[{"source_id":"abc123","result":"granted","lease_token":"<SERVER_RETURNED_TOKEN>","lease_expires_at":1234567890}]}
```

只处理 `result=granted`，并保存**服务器实际返回**的令牌。遇到 `completed`、`in_progress` 则跳过。每次最多认领 30 个来源 ID。租约到期应重新认领，不得重用过期令牌。

### 2.3 准备完整内容

`site` 使用来源站点标识；`source_id` 必须是来源站点稳定的原帖 ID，不要随机生成。Reddit 的 `source_id` 必须是 1–15 位小写字母或数字。其他校验见 `src/collect.ts`。

导入前确保标题、正文、全部一级评论、全部楼中楼以及父子关系准确。评论树使用嵌套 `replies`，**不要展平**。服务器自动生成评论 ID。

限制：标题 1–200 字符；主帖正文 1–30000 字符；每条评论 1–12000 字符；评论加楼中楼总计最多 49 条；嵌套最多 8 层。内容不完整或超过限制时，跳过并释放认领，**不得默默截断后标为完整**。

### 2.4 完成导入

`POST /api/collect/complete` 的完整请求示例（**全部为虚构占位内容，不要实际导入**）：

```json
{
  "site":"reddit",
  "source_id":"abc123",
  "lease_token":"<SERVER_RETURNED_TOKEN>",
  "topic":{
    "title":"Example recovery story",
    "body":"Example original post body.",
    "source_lang":"en",
    "comments":[
      {"body":"Example first-level comment.","source_lang":"en",
       "replies":[
         {"body":"Example second-level reply.","source_lang":"en",
          "replies":[{"body":"Example third-level reply.","source_lang":"en"}]}
       ]},
      {"body":"Another first-level comment.","source_lang":"en"}
    ]
  }
}
```

调用：

```bash
curl -sS -X POST 'https://dev-gambling-community.119shenhao.workers.dev/api/collect/complete' \
 -H 'Content-Type: application/json' \
 --data @complete.json
```

先把**实际**请求 JSON 保存为 `complete.json`；占位 `lease_token` 不能使用。可选 `topic.terms` 和 `topic.symptom_duration_days` 应只在数据确实存在且满足当前代码约束时使用。语言不确定时可省略 `source_lang`，由服务端识别；不要自行改写原文。

成功响应包含 `status`、`topic_id`、`duplicate`、`imported.topics`、`imported.comments` 等字段。必须以**实际响应**为准。内容指纹重复时可能 `duplicate=true` 且新增数量为 0。来源完成后，不再为该来源增量补充评论。

### 2.5 失败释放

```bash
curl -sS -X POST 'https://dev-gambling-community.119shenhao.workers.dev/api/collect/release' \
 -H 'Content-Type: application/json' \
 --data '{"site":"reddit","source_id":"abc123","lease_token":"<SERVER_RETURNED_TOKEN>"}'
```

只有在确定尚未完成导入时释放。请求超时或结果不明，先查 exclusions 和回读结果；不能盲目重试/释放。无效、过期或不属于当前采集器的令牌可能返回 409。

## 3. 回读验收和统计

完成后检查：

1. 实际响应是否有 `topic_id`、`status`、`duplicate` 及新增数量。
2. exclusions 是否显示该 `site + source_id` 为 `completed`。
3. 通过现有读取接口或开发 D1 只读查询确认主帖、评论总数、楼中楼父子关系、正文及原文语言。
4. 内容审核可能使帖子处于非公开状态；写入成功不等于已公开显示。
5. 不能进行 D1 回读时，明确标注“API 完成，数据库回读未验证”，不能宣称端到端验收成功。

报告字段：来源、候选数、排除数、认领数、新增主帖数、新增评论数（含楼中楼）、重复数、失败数、回读状态。不要把“发现 URL”“认领成功”“提交工作流”当作实际入库。

## 4. 直接导入接口（仅用于不需要来源认领的场景）

| 方法 | 路径 | 请求结构 |
|---|---|---|
| GET | `/api/import/account` | 查询系统导入账号 |
| POST | `/api/import/topics` | 单个 topic 对象 |
| POST | `/api/import/comments` | 单个 comment 对象 |
| POST | `/api/import/batch` | `{"topics":[...],"comments":[...]}` |

单篇请求示例（示意内容）：

```json
{"title":"Example topic","body":"Example text.","source_lang":"en","comments":[{"body":"Example comment.","source_lang":"en","replies":[{"body":"Example nested reply.","source_lang":"en"}]}]}
```

追加评论示例：

```json
{"topic_id":"<EXISTING_TOPIC_ID>","parent_comment_id":null,"body":"Example comment.","source_lang":"en","replies":[]}
```

批量导入最多 10 篇主帖，并受 50 个返回项目的总限制。相同请求具有哈希幂等性（`replayed=true`）；同标题正文内容重复时跳过整篇及其附带回复。正常外部采集应使用 collect 而非绕过认领。

## 5. 当前采集器与代码位置

- `src/index.ts`：路由与 health
- `src/collect.ts`：exclusions、claim、complete、release、queue 的真实参数校验
- `src/import.ts`：直接导入与幂等
- `scripts/gambling_collect.py`：Python 采集执行器
- `scripts/gambling_sources.json`：来源配置
- `.github/workflows/gambling-collector-on-demand.yml`：按需采集工作流
- `docs/COLLECTION_AND_SYNC.md`：开发/生产内容同步与验收记录

目前 `scripts/gambling_sources.json` 已登记 GamCare 与 Gambling Therapy 两个来源，其中 **GamCare 在用户明确确认取得完整主帖和评论再发布许可后已启用**（用户声明如实登记；没有独立核验许可文件），Gambling Therapy 仍未启用且列表 HTTP 403。`scripts/gambling_forums.py` 实现独立发现及严格 HTML 正文/回复解析；`scripts/gambling_collect.py` 的 `inspect` 可以只读检查及核实已完成帖子，`collect` 会检查 `approved`、`parser_verified`、`reuse_allowed` 和 `permission_evidence` 后执行 `exclusions → claim → complete → 多页回读`。GamCare **已实测自动新增真实 9 篇主帖、49 条回复**（见下文记录），但这不是其它来源可用的证明。未启用的来源在正式采集模式中直接跳过。

GitHub 请求文件 `.github/gambling-collector-request.json` 的格式为：

```json
{"request_id":"<UNIQUE_REQUEST_ID>","mode":"collect","sites":["all"],"candidates":{},"limit":2}
```

仅提交请求文件不代表采集完成；还需检查 Actions 实际运行结果及开发 D1 入库。

## 6. 给第三方 AI 的最终执行指令

先阅读本指南，再核对 `dev` 分支 `src/collect.ts`、`src/import.ts`。先检查线上 health；按 **exclusions → claim → 完整解析 → complete → 回读验证** 的顺序操作；失败则 release。只写开发环境，不直接写生产。使用真实来源 ID、完整评论树和服务器签发的租约令牌。每次提交后报告真实新增与重复数量，不能猜测成功。

### 2026-11-22 新解析器和独立采集工作流核验

- [GitHub Actions 真实只读来源发现 #44992825630](https://github.com/119shenhao/gambling/actions/runs/44992825630)：GitHub Runner 访问开发 Worker 成功、10 项离线解析测试通过、GamCare 候选 39 篇；没有导入。
- 正文解析探测：`mode=inspect` 会对每个来源前两篇候选验证完整正文和评论数，只记录验证数量或失败原因，不记录原文内容；待检查实际新运行结果。
- 所有外部采集仅可写 gambling DEV；`src/collect.ts` 的租约、去重、原子完整评论导入仍是最终门禁。

### 2026-11-22 GamCare 已验收执行记录（截至本轮）

- [首篇真导入](https://github.com/119shenhao/gambling/actions/runs/44993497291)：1 主帖、7 回复。
- [自动采集及误判记录](https://github.com/119shenhao/gambling/actions/runs/44993558005)：有 2 篇因服务端对短评论独立识别为 `und`，旧代码误报 `readback_reply_mismatch`；[只读再核验](https://github.com/119shenhao/gambling/actions/runs/44993908744) 已确认14条和7条真实评论全文完整。
- [首次自动验收成功](https://github.com/119shenhao/gambling/actions/runs/44993765907)：2 篇、7 回复、错误0。
- [最新恢复自动采集默认命令](https://github.com/119shenhao/gambling/actions/runs/44994042299)：2 篇、10 回复、错误0、17项解析器测试通过、Actions 成功。
- 原站正文及评论内容保留，服务端原文语言为自动检测结果；评论提示 `en` 不应强制覆盖服务端 `und`。每篇仍按原站稳定 source_id 去重并由系统账户显示 Anonymous；不会因检测语言不一致重复提交。
- 当前 GitHub 请求默认保持 `mode=collect`、`sites=["all"]`、`candidates={}`、`limit=2`，仅向戒赌独立 DEV D1 写入。开发→生产独立同步不属于本接口指南中的采集动作。
