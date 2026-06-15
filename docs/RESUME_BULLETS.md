# Resume Bullets — StudyPilot AI

## 中文简历描述

### 项目名称
StudyPilot AI：基于 RAG 与 Agent Workflow 的个性化 AI 学习教练系统

### 项目描述
独立设计并开发了一款面向大学生的 AI 学习教练应用，支持教材、真题、PPT 等课程资料的智能解析，构建 concept/formula/example/exam-pattern/figure 五维结构化知识库，通过 Agent Workflow 理解用户学习目标并生成个性化学习路径，基于 Typst 出版级排版引擎输出四类正式教学 PDF（考前冲刺、真题精讲、模拟试卷、章节复习）。

### 技术栈
Python · Streamlit · PyMuPDF · FAISS · sentence-transformers · DeepSeek API · Typst · Jinja2

### 项目亮点

1. **个性化学习画像系统** — 设计 UserProfile 数据模型和 PersonalizationEngine 推荐引擎，将用户自然语言目标（如"明天考电磁场，只有3小时"）解析为结构化学计划，包含场景识别、PDF 类型推荐、时间分配和薄弱点优先复习路径。

2. **五维结构化知识库** — 构建 concept → formula → example → exam-pattern → figure 知识图谱，支持关键词匹配和向量检索，实现课程资料的智能关联和考点覆盖分析。

3. **Agent Workflow 与 Wizard Flow** — 设计多步骤 Agent 引导流程（Home → Goal → Upload → Preferences → Results），集成非阻塞后台任务生成，用户可随时切换页面、查看进度和下载结果。

4. **Typst PDF 引擎** — 基于 Typst 出版级排版系统生成四类教学 PDF：考前 30 分钟 Sprint 救命册（5-8p）、真题精讲 PastPaper（8-12p）、模拟试卷 MockExam（8-12p）和章节复习讲义 Review（18-25p），支持公式原生渲染、教学插图和来源引用。

5. **Figure Engine 图像资产系统** — 设计教材/PPT/真题图像提取、概念匹配、多维度评分和选择框架，支持来源优先级策略和 fallback 机制，为教学插图从程序化 SVG 升级为教材原图奠定基础。

6. **Document Intelligence v5 架构** — 设计开源文档智能工具的统一接入层（ParserRegistry），预留 MinerU、Marker、PaddleOCR、DocLayout-YOLO 等适配器接口，当前已成功接入 Marker 和 DocLayout-YOLO。

---

## English Resume Bullets

### Project Name
StudyPilot AI: Personalized AI Learning Coach Powered by RAG & Agent Workflow

### Brief
Built a full-stack AI learning coach for university students that parses course materials (textbooks, past exams, PPTs), constructs a structured knowledge graph across concepts/formulas/examples/exam-patterns/figures, and generates four types of professional teaching PDFs via a Typst publishing engine — all driven by a natural-language goal parser and personalization engine.

### Tech Stack
Python · Streamlit · PyMuPDF · FAISS · sentence-transformers · DeepSeek API · Typst · Jinja2

### Key Achievements

1. **Personalized Learning Profile** — Designed a UserProfile data model and PersonalizationEngine that converts free-text learning goals (e.g., "exam tomorrow, 3 hours left, weak on Gauss and image method") into structured plans with scenario detection, PDF type recommendation, time allocation, and weak-point prioritization.

2. **Five-Dimensional Knowledge Graph** — Built a concept → formula → example → exam-pattern → figure knowledge graph supporting keyword matching and vector retrieval for intelligent content association and syllabus coverage analysis.

3. **Agent Workflow System** — Implemented a multi-step wizard flow (Home → Goal → Upload → Preferences → Results) with non-blocking background task execution, real-time progress tracking, and persistent output management.

4. **Typst PDF Publishing Engine** — Developed four professional PDF types using the Typst typesetting system: Sprint (5-8p, last-minute review), PastPaper (8-12p, exam question analysis), MockExam (8-12p, simulated tests), and Review (18-25p, chapter study notes) — with native math rendering, teaching diagrams, and source citations.

5. **Figure Engine** — Built an image asset pipeline that extracts, tags, matches, scores, and selects teaching figures from textbooks/past-papers/PPTs, with source-type prioritization and honest fallback reporting.

6. **Document Intelligence Adapter Layer** — Architected a ParserRegistry system that auto-selects the best available open-source document parser (Marker, DocLayout-YOLO, MinerU, PaddleOCR), with robust fallback to PyMuPDF when advanced tools are unavailable.
