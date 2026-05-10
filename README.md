# 精读 (IntensiveReading)

辅助精读复杂长文本的工具。对文本进行自动分词，支持为每个词定义指代对象和标注样式，并提供分词修正（拆分/合并）功能。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, SQLAlchemy, jieba |
| 前端 | TypeScript, React 18, Vite, Tailwind CSS, Zustand |
| 数据库 | SQLite |
| 包管理 | uv (Python), npm (Node.js) |

## 项目结构

```
├── main.py                  # FastAPI 应用入口
├── models.py                # SQLAlchemy 数据模型
├── database.py              # 数据库连接配置
├── services/tokenizer.py    # jieba 分词服务
├── routers/documents.py     # API 路由
├── frontend/
│   └── src/
│       ├── types/index.ts       # 类型定义
│       ├── api/index.ts         # API 请求层
│       ├── store/index.ts       # Zustand 状态管理
│       └── components/
│           ├── App.tsx           # 路由配置
│           ├── HomePage.tsx      # 首页（文档列表 + 上传）
│           ├── ReaderPage.tsx    # 阅读页
│           ├── Toolbar.tsx       # 工具栏（查看/拆分/合并/保存）
│           ├── TextCanvas.tsx    # 分词文本渲染
│           ├── TokenSpan.tsx     # 单个分词组件
│           ├── TokenPopover.tsx  # 悬浮指代卡片
│           ├── TokenSplitModal.tsx # 拆分弹窗
│           └── ReferentEditor.tsx  # 指代编辑器
```

## 快速开始

```bash
# 1. 启动后端
source .venv/bin/activate && python main.py
# 运行于 http://localhost:8000

# 2. 启动前端（新终端窗口）
cd frontend && npm run dev
# 运行于 http://localhost:5173
```

## 功能

- **自动分词**：上传文本后，后端使用 jieba 进行中文分词
- **视觉区分**：分词按样式类型以不同下划线颜色展示（默认/关键词/命名实体/未知/标点符号/数字）
- **指代查看**：hover 分词时弹出悬浮卡片，显示该词的指代目标或注释
- **指代编辑**：点击分词选中后，可设置文中指代、外部链接或文字注释
- **分词修正**：
  - 拆分模式：点击分词，在弹窗中选择拆分位置将一个词拆为两个
  - 合并模式：依次点击两个相邻分词将其合并
- **修改保存**：分词和指代修改通过 API 持久化到 SQLite

## 数据模型

### Token

| 字段 | 说明 |
|---|---|
| `start_offset` | 在原文中的起始字符位置 |
| `text` | 分词文本 |
| `style_type` | 样式类型：`default` / `keyword` / `entity` / `unknown` / `punctuation` / `number` |
| `ref_type` | 指代类型：`internal` / `external` / `note` |
| `ref_target_token_id` | 文中指代的目标 token id |
| `ref_url` | 外部链接 URL |
| `ref_explanation` | 文字注释 |

### API

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/documents` | 创建文档（自动分词） |
| `GET` | `/api/documents` | 文档列表 |
| `GET` | `/api/documents/:id` | 获取文档及分词 |
| `PUT` | `/api/documents/:id/tokens` | 批量更新分词 |
| `PATCH` | `/api/tokens/:id` | 更新单个分词的指代/样式 |

## TODO

### 后端

- [ ] 分词服务支持自定义词典（用户词典），提升专业术语分词准确度
- [ ] 支持更多分词器（pkuseg、lac 等）可切换
- [ ] 添加段落级别的结构信息（标题、列表、代码块）
- [ ] Token 修改历史记录（undo/redo）
- [ ] 导出分词和指代数据（JSON/Markdown）

### 前端

- [ ] 拆分/合并操作支持撤销
- [ ] 支持键盘快捷键（切换模式、撤销、保存）
- [ ] Token 列表侧边栏（快速定位和跳转）
- [ ] 指代关系可视化（箭头/连线标注文中指代）
- [ ] 暗色主题
- [ ] 响应式布局（移动端适配）
- [ ] 批量修改样式类型（多选后统一设置）

### 分词与 NLP

- [ ] 自动识别标点符号并标记为 `punctuation` 样式
- [ ] 自动识别数字并标记为 `number` 样式
- [ ] 自动提取命名实体（人名、地名、机构名）并标记为 `entity` 样式
- [ ] 支持英文文本分词

### 工程

- [ ] 前端单元测试
- [ ] 后端 API 测试
- [ ] CI/CD 配置
- [ ] Docker 容器化部署
