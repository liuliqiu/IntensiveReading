# 精读 (IntensiveReading)

辅助精读复杂长文本的工具。对文本进行自动分词，支持为分词标注样式类型，并通过关系系统建立分词之间、分词与文本注释之间的语义关联。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, jieba |
| 前端 | TypeScript, React 18, Vite, Tailwind CSS, Zustand |
| 存储 | JSON 文件 |
| 包管理 | uv (Python), npm (Node.js) |

## 项目结构

```
├── main.py                     # FastAPI 应用入口
├── storage.py                  # 文件存储层（含数据迁移逻辑）
├── services/tokenizer.py       # jieba 分词服务
├── routers/documents.py        # API 路由
├── frontend/
│   └── src/
│       ├── types/index.ts          # 类型定义
│       ├── api/index.ts            # API 请求层
│       ├── store/index.ts          # Zustand 状态管理
│       └── components/
│           ├── App.tsx              # 路由配置
│           ├── HomePage.tsx         # 首页（文档列表 + 上传）
│           ├── ReaderPage.tsx       # 阅读页
│           ├── Toolbar.tsx          # 工具栏（保存）
│           ├── TextCanvas.tsx       # 分词文本渲染
│           ├── TokenSpan.tsx        # 单个分词组件
│           └── TokenActionPanel.tsx # 侧边栏（样式/关系/操作）
```

## 快速开始

```bash
# 1. 启动后端
uv run python main.py
# 运行于 http://localhost:8000

# 2. 启动前端（新终端窗口）
cd frontend && npm run dev
# 运行于 http://localhost:5173
```

## 功能

- **自动分词**：上传文本后，后端使用 jieba 进行中文分词，同一词汇的多次出现合并为一个 Token
- **样式标注**：分词按样式类型以不同样式展示（default / keyword / entity / unknown / punctuation / number / connector）
- **关系系统**：
  - **关系对象（RelationObject）**：将分词转为独立的关系对象，或直接创建文本对象
  - **关系（Relation）**：从已有关系对象中选择 2 个以上，建立语义关联（指代 / 属于 / 链接 / 注释 / 自定义）
- **分词修正**：支持按含义拆分、按字符拆分、合并相邻分词
- **修改持久化**：所有修改通过 API 保存到 JSON 文件

## 数据模型

数据以 JSON 文件存储在 `data/documents/<id>.json`。

### Token（分词）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `start_offsets` | number[] | 在原文中的所有出现位置 |
| `text` | string | 分词文本 |
| `style_type` | string | 样式类型 |

### RelationObject（关系对象）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `token_id` | string\|null | 关联的 Token ID（与 `text` 互斥） |
| `text` | string\|null | 文本内容（与 `token_id` 互斥） |

> 约束：同一 Token 最多对应一个 RelationObject。

### Relation（关系）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 唯一标识 |
| `type` | string | 关系类型：`refers_to` / `belongs_to` / `links_to` / `annotates` / 自定义 |
| `object_ids` | string[] | 引用的 RelationObject ID 列表（有序，至少 2 个） |

> 关系类型定义对象间的语义。如 `refers_to` 表示 object_ids[0] 指代 object_ids[1]。

### API

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/documents` | 创建文档（自动分词） |
| `GET` | `/api/documents` | 文档列表 |
| `GET` | `/api/documents/:id` | 获取文档完整数据 |
| `PUT` | `/api/documents/:id` | 保存文档（tokens + relation_objects + relations） |
| `POST` | `/api/tokens/:id/split` | 拆分指定 Token |

### 数据迁移

存储层包含自动迁移逻辑，按以下顺序执行：
1. `_migrate_refs_to_relations` — 将旧版 Token 上的 `ref_*` 字段转为独立的 Relation
2. `_migrate_relations_to_objects` — 将旧版 Relation（source_token_id/target_*）转为 objects 格式
3. `_migrate_objects_to_top_level` — 将内嵌 objects 提取为顶层 relation_objects 池

迁移在每次读取文档时自动执行，无需手动干预。
