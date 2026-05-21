# 精读 (IntensiveReading)

辅助精读复杂长文本的工具。对文本进行自动分词，支持为分词标注样式类型，并通过关系系统建立分词之间、分词与文本注释之间的语义关联。支持通过 AI 对文本进行总结和术语解释。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, jieba, openai, trafilatura, playwright, beautifulsoup4 |
| 前端 | TypeScript, React 19, Vite, Tailwind CSS, Zustand |
| 存储 | JSON 文件 |
| AI | DeepSeek（兼容 OpenAI 协议，可替换） |
| 包管理 | uv (Python), npm (Node.js) |

## 项目结构

```
├── main.py                       # FastAPI 应用入口
├── storage.py                    # 文件存储层（含数据迁移逻辑）
├── opencode.json                 # opencode 项目配置
├── AGENTS.md                     # opencode 行为约定
├── services/
│   ├── tokenizer.py              # jieba 分词 + 概念感知分词 + 词汇表分词
│   ├── ai.py                     # AsyncOpenAI 客户端（摘要/解释/概念分析）
│   └── scraper.py                # 网页抓取（静态 + JS 渲染）
├── routers/documents.py          # API 路由（文档 + 文本层 + AI 操作 + 统一处理）
├── tests/
│   └── test_tokenizer.py         # 分词单元测试
├── frontend/
│   └── src/
│       ├── types/index.ts            # 类型定义
│       ├── api/index.ts              # API 请求层
│       ├── store/index.ts            # Zustand 状态管理
│       └── components/
│           ├── App.tsx                # 路由配置
│           ├── HomePage.tsx           # 首页（文档列表 + 上传）
│           ├── ReaderPage.tsx         # 阅读页（原文/摘要切换）
│           ├── Toolbar.tsx            # 工具栏（视图切换 + AI 操作）
│           ├── TextCanvas.tsx         # 分词文本渲染
│           ├── SummaryCanvas.tsx      # 摘要文本渲染
│           ├── TokenSpan.tsx          # 单个分词组件
│           └── TokenActionPanel.tsx   # 侧边栏（样式/关系/操作/AI）
```

## 快速开始

```bash
# 0. 配置 AI API Key（可选，不配置则无法使用摘要和解释功能）
# 网页抓取需要系统安装 Google Chrome（JS 渲染页面的兜底方案，静态页面无需）
# macOS 上通常已预装，无需额外操作
export OPENAI_API_KEY=sk-your-deepseek-key
#默认为 DeepSeek，如需使用 OpenAI，还需设置：
#export OPENAI_BASE_URL=https://api.openai.com/v1
#export OPENAI_MODEL=gpt-4o-mini

# 1. 启动后端
uv run python main.py
# 运行于 http://localhost:8000

# 2. 启动前端（新终端窗口）
cd frontend && npm run dev
# 运行于 http://localhost:5173
```

## 功能

- **自动分词**：上传文本后，后端使用 jieba 进行中文分词，同一词汇的多次出现合并为一个 Token
- **统一处理流程**：点击「提交并分析」，自动执行以下流程：
  1. 创建文档 + 摘要层骨架
  2. AI 对原文进行摘要
  3. AI 提取关键概念及其语义关系
  4. 将概念名注册到 jieba 以对原文进行概念感知分词
  5. 对摘要使用原文词汇表分词（复用 Token ID）
- **概念感知分词**：AI 提取的文中关键概念（如「Transformer架构」「注意力机制」）会被注册为 jieba 自定义词汇，确保分词时作为完整单元提取。概念词样式标记为 `keyword`（蓝色下划线），其余词汇无特殊样式
- **样式标注**：分词按样式类型标注（default / keyword / punctuation / number / connector），仅 keyword 在阅读界面有视觉样式
- **关系系统**：
  - **关系对象（RelationObject）**：将分词转为独立的关系对象，或直接创建文本对象。支持手动创建和 AI 解释生成
  - **关系（Relation）**：从已有关系对象中选择 2 个以上，建立语义关联（指代 / 属于 / 链接 / 注释 / 解释 / 自定义）
   - **跨文档知识共享**：关系对象和关系存储在全局知识库中，所有文档共享同一套知识网络。对象与文档的所属关系通过 `belongs_to` 关系表达，文档本身以 `kind: "document"` 的关系对象表示
- **分词修正**：支持按含义拆分、按字符拆分、合并相邻分词
- **修改持久化**：所有修改通过 API 保存到 JSON 文件
- **AI 摘要**：点击「生成摘要」按钮，AI 对原文进行总结。摘要使用原文的词汇表进行分词（最大正向匹配），与原文共用同一套 Token ID。新出现的词汇自动加入原文词汇表。原文中对词汇的合并操作会自动反映到摘要中
- **AI 解释**：选中一个已转为关系对象的词汇，点击「AI 解释」，AI 会结合上下文对该术语在文中的含义进行解释，生成的关系存储在原文关系中
- **AI 概念分析**：在摘要视图下，点击「分析概念关系」按钮，AI 自动提取摘要中的关键概念及其语义关系，以结构化列表形式展示（因果/包含/对比/互补/递进/描述）。每个概念的描述也作为独立的关系对象存储，通过 `explains` 关系与概念名关联
- **网页抓取**：首页支持通过 URL 导入文本。输入网页链接，自动提取标题和正文。对静态页面使用 trafilatura 快速提取，对 JS 动态渲染页面（SPA）自动切换到 Playwright + 系统 Chrome 渲染后再提取

## 架构说明：统一词汇与关系

项目的核心设计理念是**原文和所有文本层（摘要等）共用同一套词汇和关系**。

- **词汇表（Vocabulary）**：文档的 `tokens` 是唯一的词汇来源。每个 TextLayer 不拥有自己的 Token，而是引用文档 Token 的 ID，仅存储该 Token 在层文本中的出现位置（`start_offsets`）
- **词汇表分词**：摘要生成后使用 `tokenize_with_vocabulary()` 分词。该函数将原文 Token 注册为 jieba 自定义词汇，然后切分摘要文本，确保已存在的 Token 复用相同 ID 和样式。新出现的词自动加入文档词汇表
- **全局知识库**：关系（Relation）和关系对象（RelationObject）存储在全局的 `knowledge.json` 中，在所有文档间共享。无论在原文视图还是摘要视图编辑关系，修改的都是同一份全局数据。在摘要中为词汇建立的关系，等同于在原文中为该词汇建立关系。对象通过 `belongs_to` 关系标识所属文档，文档本身以 `kind: "document"` 的关系对象表示
- **层扩展性**：TextLayer 的 `type` 字段支持未来扩展为其他类型（如翻译、改写等），所有层都遵循统一词汇模型

## 产品设计原则

### 信息层级：专注 vs 探索

全局知识库让所有文档共享同一套概念网络，但信息密度需要根据用户意图分层呈现：

- **关系概览（无选中分词）**：仅显示与当前文档直接相关的概念关系（即成员对象通过 `belongs_to` 关系属于当前文档）。用户进入文档时首要任务是理解本文内容，不应被其他文档的知识干扰
- **分词详情（选中分词时）**：显示该词汇在**所有文档**中的关联关系。用户主动点击一个词汇意味着进入了探索模式，此时展示跨文档的知识连接有助于深度理解

这一设计平衡了信息聚焦与知识探索的需求：默认视图减少认知负担，点击操作触发深度检索。

## 数据模型

数据存储结构：

```
data/
├── knowledge.json          # 全局关系对象与关系（跨文档共享）
├── documents/<id>.json     # 文档（原始文本 + 词汇表）
└── layers/<id>.json        # 文本层（文本 + 位置引用）
```

### Knowledge（知识库）

```json
{
  "relation_objects": [
    { "id": "uuid", "text": "文本", "kind": "manual" },
    { "id": "uuid", "text": "文档标题", "kind": "document", "metadata": { "document_id": "uuid" } }
  ],
  "relations": [
    { "id": "uuid", "type": "refers_to", "members": [{"kind": "object", "id": "uuid"}] },
    { "id": "uuid", "type": "belongs_to", "members": [{"kind": "object", "id": "uuid"}, {"kind": "object", "id": "uuid"}] }
  ]
}
```

### Document（文档）

```json
{
  "id": "uuid",
  "title": "标题",
  "original_text": "原文内容…",
  "tokens": [
    { "id": "uuid", "start_offsets": [0, 50], "text": "人工智能", "style_type": "keyword" }
  ],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### TextLayer（文本层）

```json
{
  "id": "uuid",
  "document_id": "uuid",
  "type": "summary",
  "text": "摘要内容…",
  "tokens": [
    { "id": "doc_token_uuid", "start_offsets": [5], "text": "人工智能", "style_type": "keyword" }
  ],
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

> TextLayer 的 `tokens[].id` 引用 Document 的 Token ID。`start_offsets` 是该 Token 在层文本中的位置。

### Token（分词）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `start_offsets` | number[] | 在文本中的所有出现位置 |
| `text` | string | 分词文本 |
| `style_type` | string | 样式类型 |

### RelationObject（关系对象）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `text` | string\|null | 对象文本内容 |
| `kind` | string | 来源：`manual` / `document` / `ai_explanation` / `ai_concept` / `ai_concept_desc` |
| `metadata` | object\|null | JSON 扩展元数据（如 `document_id`） |

> 约束：相同 `text` + `kind` 的对象自动合并为一个，跨文档共享。对象与文档的所属关系通过 `belongs_to` 类型的 Relation 表达。
>
> TODO: 同名词汇在不同文档中可能表达不同含义（如"苹果"可指水果或公司），当前自动合并同名对象，未来需要支持按语义区分。
>
> 注意：对象不再直接绑定 Token，而是通过文本内容匹配。同一词汇在不同文档中出现时，共用同一个 RelationObject。
>
> `belongs_to` 关系语义：`members[0] belongs_to members[1]`，即对象属于文档。文档对象本身以 `kind: "document"` 标识，其 `metadata.document_id` 存储原始文档 ID。

### Relation（关系）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `type` | string | 关系类型：`refers_to` / `belongs_to` / `links_to` / `annotates` / `explains` / `causal` / `contains` / `contrasts` / `complements` / `precedes` / `describes` / 自定义 |
| `members` | Member[] | 引用的对象列表（有序，至少 2 个，支持嵌套关系） |
| `description` | string\|null | AI 生成的关系描述（可选） |

### Member（关系成员）

| 字段 | 类型 | 说明 |
|---|---|---|
| `kind` | string | `"object"` 或 `"relation"`（支持关系嵌套） |
| `id` | string | 对应的 RelationObject ID 或 Relation ID |

> 关系类型定义对象间的语义。如 `refers_to` 表示 members[0] 指代 members[1]，`explains` 表示 members[0] 被 members[1] 解释。

### API

#### 文档

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/documents` | 创建文档（自动分词） |
| `POST` | `/api/documents/process` | 创建文档并执行完整处理流程（摘要 + 概念分析 + 概念感知分词） |
| `GET` | `/api/documents` | 文档列表 |
| `GET` | `/api/documents/:id` | 获取文档完整数据 |
| `PUT` | `/api/documents/:id` | 保存文档（仅 tokens） |
| `POST` | `/api/tokens/:id/split` | 拆分指定 Token |

#### 文本层

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/documents/:did/layers` | 创建文本层 |
| `GET` | `/api/documents/:did/layers` | 列出文档的所有文本层 |
| `GET` | `/api/layers/:lid` | 获取文本层详情 |
| `PUT` | `/api/layers/:lid` | 保存文本层的分词位置 |
| `DELETE` | `/api/layers/:lid` | 删除文本层 |

#### AI 操作

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/layers/:lid/summarize` | 对 type=summary 的层执行 AI 摘要（自动分词并复用词汇表） |
| `POST` | `/api/documents/:did/objects/:oid/explain` | 对指定关系对象执行 AI 解释 |
| `POST` | `/api/layers/:lid/concepts` | 对 type=summary 的层执行 AI 概念分析 |

#### 知识库

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/knowledge` | 返回全局关系对象和关系 |
| `POST` | `/api/knowledge/objects` | 创建关系对象（接收 `token_id?`、`document_id?`、`text?`、`kind`） |
| `DELETE` | `/api/knowledge/objects/:id` | 删除关系对象 |
| `POST` | `/api/knowledge/relations` | 创建关系 |
| `PUT` | `/api/knowledge/relations/:id` | 编辑关系 |
| `DELETE` | `/api/knowledge/relations/:id` | 删除关系 |

#### 网页抓取

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/scrape` | 抓取网页标题和正文（支持静态页面和 JS 渲染页面） |

> 静态页面使用 trafilatura 快速提取。JS 动态渲染的 SPA 页面会自动切换到 Playwright 无头浏览器（需要系统安装 Google Chrome）。

### 数据迁移

存储层包含自动迁移逻辑，按以下顺序执行：
1. `_migrate_refs_to_relations` — 将旧版 Token 上的 `ref_*` 字段转为独立的 Relation
2. `_migrate_relations_to_objects` — 将旧版 Relation（source_token_id/target_*）转为 objects 格式
3. `_migrate_objects_to_top_level` — 将内嵌 objects 提取为顶层 relation_objects 池
4. `_migrate_objects_add_kind` — 给旧版关系对象补充 `kind: "manual"` 字段
5. `_migrate_docs_to_knowledge` — 将所有文档中的关系和关系对象迁移到全局 `knowledge.json`

迁移在每次读取文档时自动执行，无需手动干预。
