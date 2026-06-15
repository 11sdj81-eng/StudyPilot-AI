# StudyPilot AI — Project Showcase

## 项目定位

StudyPilot AI 是一款面向大学生的个性化 AI 学习教练系统。用户上传教材、PPT 和真题后，AI 自动构建课程知识图谱，解析考点规律，并通过 Typst 引擎生成四类教学 PDF：考前冲刺(Sprint)、真题精讲(PastPaper)、模拟试卷(MockExam)和章节复习(Review)。

## 核心功能

| 功能 | 说明 | 状态 |
|------|------|------|
| 个性化学习画像 | 解析用户目标文本，构建 UserProfile，驱动推荐 | ✅ v1.3 |
| 自然语言目标解析 | "明天考电磁场，只有3小时" → 结构化学习计划 | ✅ v1.3 |
| 学习路径图 | 概念依赖图 + 薄弱点高亮 + 推荐 PDF 类型 | ✅ v1.3 |
| Typst PDF 引擎 | 四类 PDF：Sprint / PastPaper / MockExam / Review | ✅ v4.1 |
| Exam Pattern Engine | 题型模式库 + 难度分级 + 高频考点匹配 | ✅ v4.1 |
| Figure Engine | 教材/PPT/真题图像检索、匹配、评分、fallback | ✅ v1.0 |
| Knowledge Graph v5 | 概念 → 公式 → 例题 → 考点关联图谱 | ✅ v5 |
| RAG v5 | 课程级向量检索 + 来源引用 | ✅ v5 |
| Bunny AI 助手 | 基于用户画像的个性化学习建议和陪伴 | ✅ v1.3 |
| 输出文件管理 | Run-based 目录 + final 标记 + demo manifest | ✅ v1.3 |

## 技术架构

```
Streamlit UI (v1.3)
    ├── UserProfile (个性化学习画像)
    ├── PersonalizationEngine (推荐引擎)
    ├── Goal Parser (自然语言 → 结构化目标)
    │
    ├── Wizard Flow (Home → Goal → Upload → Prefs → Results)
    ├── Task Manager (非阻塞后台生成)
    ├── Output Manager (文件管理 + Demo Manifest)
    │
    ├── RAG Engine (PyMuPDF + FAISS + DeepSeek)
    ├── Figure Engine (PDF/PPT 图像提取 + 匹配 + 评分)
    ├── Exam Pattern Engine (题型库 + 难度分级)
    ├── Knowledge Graph v5 (概念关联图谱)
    │
    └── Typst PDF v4.1 (四类正式 PDF)
```

## Agent 工作流

1. 用户输入自然语言目标 → `goal_parser` 解析
2. 更新 `UserProfile` + 生成 `PersonalizedPlan`
3. 推荐最佳 PDF 类型和知识点优先级
4. Wizard Flow 引导：上传 → 偏好 → 生成
5. 后台线程执行 PDF 生成（非阻塞）
6. 结果页展示学习建议 + 覆盖率 + 使用场景标签

## RAG / KnowledgeGraph

- 基于 PyMuPDF 解析 PDF + FAISS 向量检索
- 文本分块 chunk_size=800, overlap=120
- 默认 Embedding: BAAI/bge-small-zh-v1.5
- TF-IDF fallback（模型下载失败时自动降级）
- 概念节点：电场、高斯、电位、边界、镜像、能量

## PDF v4.1 Typst

- 引擎：Typst CLI（正式出版级排版）
- 支持：封面、目录、正文、公式卡片、插图、来源引用
- 四类输出：Sprint (5-8p) / PastPaper (8-12p) / MockExam (8-12p) / Review (18-25p)
- 数学渲染：Typst 原生公式排版

## Document Intelligence v5 (Beta)

- ParserRegistry 自动选择最佳解析器
- Marker (marker-pdf) — 已安装，模型下载中
- DocLayout-YOLO — 包已安装，权重待修复
- MinerU / PaddleOCR — Python 3.14 环境不兼容
- 当前可用：PyMuPDF 文本提取 + 程序化 SVG

## Figure Engine

- 从 PDF/PPT 提取图像 → FigureBank → 概念匹配 → 评分 → 选图
- 支持 source_type: textbook / ppt / past_paper / programmatic / redraw
- 质量检查：分辨率、扫描页检测、去重、概念匹配验证
- 当前：教材为扫描版，使用程序化 SVG fallback

## Exam Pattern Engine

- 题型：选择题(choice) / 填空题(fill) / 简答题(short) / 计算综合(compute/comprehensive)
- 难度：Level 2-5 分级
- 高频考点：高斯分段、镜像边界、电位负号、能量比例

## UI 截图占位

- [ ] 首页 Hero + 今日状态卡
- [ ] Agent 输入框 + AI 理解结果展示
- [ ] 学习路径图（薄弱点高亮 + 优先复习标注）
- [ ] Wizard Flow 偏好设置页
- [ ] 结果页：学习建议 + 覆盖率 + 使用场景标签
- [ ] 输出文件管理页
- [ ] Bunny AI 助手卡片

## Demo 流程

1. 启动 `streamlit run app.py`
2. 首页 Agent 输入：`明天考电磁场，我只有3小时，高斯定理和镜像法不稳`
3. 查看 AI 理解结果 + 今日状态卡
4. 设置目标分数、学习水平、薄弱点
5. 上传教材 PDF + 真题 PDF（模拟数据可用于 demo）
6. 设置偏好：输出风格、插图策略、真题驱动
7. 生成 PDF（推荐 Sprint + PastPaper）
8. 查看结果页：学习建议 + 覆盖率 + 使用场景标签

## 当前限制

- 教材 PDF 为扫描版时，Figure Engine 无法自动提取插图（需人工裁剪或 MinerU OCR）
- MinerU / PaddleOCR 在 Python 3.14 + macOS arm64 环境下不可用
- Typst 需要 CLI 环境（`brew install typst`）
- DeepSeek API 需要有效 Key（`.env` 配置）

## 后续规划

1. 接入 EasyOCR 作为 macOS arm64 OCR 方案
2. DocLayout-YOLO 权重下载修复后启用版面检测
3. Marker 模型下载完成后接入 OCR + 公式 + 表格提取
4. 多语言支持完善（目前支持中/英）
5. 移动端 Web App 适配
6. 学习数据分析 Dashboard
