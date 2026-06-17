"""v2.2: Textbook-aligned teacher-lecture generation prompts.

Every prompt now enforces:
- Textbook-first: align with uploaded materials' symbols and wording
- Teacher-lecture style: not AI summary, but what a professor would hand out
- Per-knowledge-point depth: meaning → importance → derivation → teaching → exam
- Source-anchored: never claim "真题" without an actual past-exam source
"""

TASK_LABELS = {
    "single_chapter": "单章精学",
    "chapter_review": "整章复习",
    "exam_sprint": "考前冲刺",
    "hotspots": "高频考点",
    "mock_exam": "模拟试卷",
    "past_paper": "真题精讲",
    "learning_plan": "学习计划",
    "qa": "智能问答",
    "custom": "自定义生成",
}

# ---------------------------------------------------------------------------
# Shared rules appended to every lecture prompt
# ---------------------------------------------------------------------------

LATEX_RULES = """
## 数学公式格式要求

- 行内公式：$E = \\frac{F}{q}$
- 独立公式（必须编号，如 (1-1)）：
$$
\\oint_S \\mathbf{E} \\cdot d\\mathbf{S} = \\frac{Q_{\\mathrm{enc}}}{\\varepsilon_0} \\tag{1-1}
$$
- **绝对禁止** \\[ ... \\] 或裸露 LaTeX 命令
- 所有公式中的希腊字母必须使用标准写法：\\varphi、\\varepsilon、\\rho、\\theta、\\nabla
- **绝对禁止** 写出 phi、epsilon、rho、sqrtr、hatz、hatx、haty、Rhat、piε、x^2、a^2 等程序化伪符号
- 如果资料中没有出现闭合积分符号，不要主动使用闭合积分符号；优先沿用资料中的普通积分/面积分写法
- 公式编号统一使用 \\tag{1-1}、\\tag{1-2}，不要写 tag1-1
"""

TEXTBOOK_ALIGNMENT = """
## 教材对齐要求（极其重要）

1. **符号对齐**：教材用什么符号你就用什么符号。如果教材用 φ 就不要写成 ϕ，反之亦然。
2. **术语对齐**：教材叫"电位移矢量"就不要写"D矢量"，教材叫"电势"就不要全写"电位"。
3. **章节对齐**：尽量沿用教材的章节组织方式。
4. **表述对齐**：定义和定理的表述尽量对齐教材原文，但不要大段照抄。
5. **不确定时**：优先使用通用课程规范，并在旁边标注"本讲义符号体系已尽量对齐上传教材"。
"""

FIGURE_REQUIREMENT = """
## 教学插图要求

- 可以在正文中写“建议配图：...”描述图意，但不要输出 Markdown 图片链接
- 绝对不要输出 placeholder、占位图、图片暂不可用
- 插图会由系统选择高置信教材资产或生成少量专业示意图，正文不要为了凑图而虚构图
- 推荐图型：高斯面图、镜像法图、边界条件图、等位线图、知识地图
"""

SOURCE_RULES = """
## 引用格式要求

- 引用教材使用：**[教材1]**、**[教材2]**
- 引用往年题使用：**[真题1]**、**[真题2]**
- 引用其它资料使用：**[资料1]**
- **绝对禁止**在没有真实来源时声称"真题""往年题"
- **绝对禁止**在正文中出现 SS号、General Information、OCR 元数据
"""

STRUCTURE_RULES = """
## 输出结构（严格按此顺序，不得省略任何小节）

# 本章定位
（本知识点在后续章节/考试中的作用，为什么重要）

# 学习目标
（5 条具体、可检验的目标，不要写空 bullet）

# 知识地图
（文字描述知识点逻辑关系，2–3 段）

# 核心知识精讲

每个知识点（至少 5 个）必须包含：

## 知识点 N：标题
### 教材表述
（对齐教材表述，简要说明概念/定理的核心内容）

### 为什么重要
（在课程体系和考试中的地位）

### 公式推导链
（从基本方程出发，展示关键推导步骤，标注适用条件）

### 老师讲法
（用学生容易理解的方式重新解释）

### 考试考法
- 选择题怎么考
- 填空题怎么考
- 计算题怎么考
- 综合题怎么考

### 易错点
- 错误理解
- 正确判断方法

# 公式总结表

| 编号 | 公式 | 物理意义 | 适用条件 | 来源 |
|------|------|----------|----------|------|
| (1-1) | ... | ... | ... | [教材] p.X |

至少列出本章 5 个核心公式。

# 典型例题

至少 3 道完整例题。每道题必须包含以下全部字段：

## 例题 1：基础概念题
**题目：** （完整的真实考试风格题干，至少 80 字，包含物理情景、已知条件、求解目标）
**考点：** （明确指出本题考查的知识点，如"高斯定理+球对称电场"）
**难度：** ★★☆☆☆（用星级标注，1-5 星）
**常见考法：** （说明期末会如何变形考）
**解题模板：** （列出 3-5 步通用套路）
**思路分析：** （解题的切入点和关键步骤说明，不是直接写解答）
**标准解答：** （完整、规范的计算过程，每一步写清楚依据；计算题不得跳步）
**易错提醒：** （本题最容易出错的地方，以及如何避免）
**题型总结：** （这类题的通用解法归纳，让学生做一道会一类）
**类题/真题关联：** （教材例题 X.X / 往年题 20XX 第 X 题 / 改编 — 如实标注）

## 例题 2：标准计算题
**题目：**
**考点：**
**难度：** ★★★☆☆
**常见考法：**
**解题模板：**
**思路分析：**
**标准解答：**
**易错提醒：**
**题型总结：**
**类题/真题关联：**

## 例题 3：综合提高题
**题目：**
**考点：**
**难度：** ★★★★☆
**常见考法：**
**解题模板：**
**思路分析：**
**标准解答：**
**易错提醒：**
**题型总结：**
**类题/真题关联：**

# 高频考点
（结合教材和往年题分析，至少 3 个）

# 真题/往年题关联
（说明知识点在已上传往年题中的出现方式和典型考法）

# 考前速记
（最重要的公式、概念、易错点，做成速记清单）

# 自测题
至少 5 道，附答案和简要解析。
"""


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_context(chunks: list[dict]) -> str:
    lines = []
    for index, chunk in enumerate(chunks, start=1):
        source = (
            f"{chunk.get('filename', '未知文件')} "
            f"p.{chunk.get('page', '?')} "
            f"[{chunk.get('resource_type', '')}]"
        )
        lines.append(f"[资料{index} | {source}]\n{chunk.get('text', '')}")
    return "\n\n".join(lines)


def _task_header(course: dict, profile: dict, task_type: str, user_request: str) -> str:
    task_label = TASK_LABELS.get(task_type, "自定义生成")
    return f"""
课程：{course.get('university', '')}《{course.get('course_name', '')}》
考试日期：{course.get('exam_date', '')}
学习画像：{profile}
任务类型：{task_label}
用户需求：{user_request}
""".strip()


def build_generation_prompt(
    task_type: str,
    user_request: str,
    course: dict,
    profile: dict,
    chunks: list[dict],
) -> str:
    context = build_context(chunks)
    header = _task_header(course, profile, task_type, user_request)
    try:
        from core.subject_type import detect_subject_type, subject_prompt_hint
        subject_type = detect_subject_type(course)
        subject_block = subject_prompt_hint(subject_type)
    except Exception:
        subject_type = "engineering"
        subject_block = "学科类型：理工工程类。生成倾向：公式推导、示意图、工程例题、计算题。"
    try:
        from core.textbook_style_analyzer import analyze_textbook_style, style_summary_for_display
        style = analyze_textbook_style(chunks, course)
        style_note = style_summary_for_display(style)
        formula_style = style.get("formula_style", {})
        style_block = (
            f"教材风格分析：{style_note}\n"
            f"积分符号偏好：{formula_style.get('integral_style', 'ordinary')}；"
            f"允许的积分符号类型：{formula_style.get('allowed_integrals', ['ordinary'])}"
        )
    except Exception:
        style_block = "教材风格分析：未能自动分析，请严格依据检索资料原文。"

    context_block = (
        f"可参考的课程资料（**符号、术语、表述必须优先对齐以下资料**）：\n{context}"
        if context
        else "当前没有检索到课程资料，请使用通用课程规范生成内容，并提醒用户上传教材可大幅提升符号和表述一致性。"
    )

    shared = subject_block + "\n\n" + LATEX_RULES + TEXTBOOK_ALIGNMENT + FIGURE_REQUIREMENT + SOURCE_RULES + STRUCTURE_RULES

    if task_type in {"single_chapter", "chapter_review", "hotspots", "custom"}:
        body = f"""
{header}

{style_block}

{context_block}

{shared}

## 角色设定

你是一名经验丰富的大学课程老师，正在为你班上的学生编写一份**期末复习讲义**。
这不是 AI 总结，这是**老师亲手写的教辅资料**。

**写作风格要求（极其重要）：**
- 像老师在课后发给学生的补充讲义，不要像维基百科或教科书目录。
- 用"我们来看……""同学们注意……""这里容易出错的是……"这样的口吻。
- 每个概念先讲"是什么"，再讲"为什么重要"，再讲"怎么用"，最后讲"怎么考"。
- 公式不是堆出来的，每个公式都要解释每个符号的物理意义。
- 例题不能只有解答，必须包含：题目、考点标注、难度、思路分析、标准解答、易错提醒、题型总结。
- 不要在正文中反复出现"公式""公式总结""公式如下"等重复字样，让公式自然地融入讲解。
- 教材上怎么写符号，你就怎么写。不要自己发明符号。

要求：
1. **教材优先**：所有符号、术语、表述必须对齐上传教材。如果教材用 D 形式的高斯定理，就用 D；如果教材用 E，就用 E。
2. **老师口吻**：不要写得像维基百科。用老师给学生讲解的方式写。多用"注意""关键""记住""考试常考"等教学用语。
3. **考试导向**：每个知识点都要讲清楚考试怎么考。选择题怎么出、填空题怎么挖空、计算题怎么考、综合题怎么串。
4. **推导必须**：核心公式必须有完整推导链，从基本定义或基本方程出发，每一步标注依据。
5. **例题有来源**：例题优先来自教材或往年题，改编题必须标注"改编"，不允许凭空说"真题"但没有真实来源。
6. **符号干净**：绝对不出现程序化伪符号（phi、epsilon、sqrtr、hatz、hatx、haty、Rhat、piε、4piε₀、x^2、a^2 等）。所有公式编号使用 \\tag{{(1-1)}} 格式。
"""
    elif task_type == "exam_sprint":
        body = f"""
{header}

{style_block}

{context_block}

{LATEX_RULES}{TEXTBOOK_ALIGNMENT}{SOURCE_RULES}

请生成一份**考前 30 分钟冲刺讲义**，必须短、准、能背，目标页数 5-10 页。

# 考前使用说明
说明这份材料适合考前半小时如何浏览。

# 必背公式
列出 8-12 条最重要公式，每条包含：公式、适用条件、常见陷阱。

# 高频考法
按选择/填空/计算/综合题列出，必须结合已上传教材或真题来源。

# 易错点清单
至少 8 条，写成“错误做法 → 正确做法”。

# 考前口诀
给出 5-8 条有记忆价值的口诀，不要空泛。

# 最后 10 分钟检查表
写成可勾选清单，避免废话。

要求：不要长篇推导，不要铺垫历史背景，不要写 AI 总结式废话。
"""
    elif task_type == "mock_exam":
        body = f"""
{header}
{context_block}
{LATEX_RULES}{TEXTBOOK_ALIGNMENT}{SOURCE_RULES}

请根据课程教材和真题题型，生成一份正式模拟试卷。

# 试卷说明
包含考试时间、总分、答题要求。

# 一、选择题（至少 5 题，每题 4 分）
# 二、填空题（至少 5 题，每题 4 分）
# 三、计算题（至少 3 题，每题 15-20 分）
# 详细解析
每题必须有标准答案和关键步骤。

# 评分标准
按题号列出分值和扣分点。排版要像真实试卷。
"""
    elif task_type == "past_paper":
        body = f"""
{header}
{context_block}
{LATEX_RULES}{TEXTBOOK_ALIGNMENT}{SOURCE_RULES}

请生成一份**真题精讲讲义**，只基于检索到的往年题/试卷来源，不要伪造真题。

# 真题概览
列出识别到的真题来源、题型和涉及知识点。

# 考点拆解
逐题说明考查知识点、命题意图和常见失分点。

# 真题精讲
每道题包含：原题/题意转述、考点、解题思路、标准解答、易错提醒、阅卷扣分点。

# 变式题
每个核心题型给 1 道变式题，附答案与简析。

# 考前提醒
总结这份真题暴露出的高频考法和复习优先级。
"""
    elif task_type == "learning_plan":
        body = f"""
{header}
{context_block}
{LATEX_RULES}

请生成个性化学习计划：
# 总体时间规划
# 每日学习任务（具体内容 + 预计耗时）
# 阶段复习重点
# 练习任务
# 验收标准
"""
    elif task_type == "qa":
        body = f"""
{header}
{context_block}
{LATEX_RULES}{SOURCE_RULES}

请以大学助教答疑的方式直接回答，引用来源时用 [教材] / [真题] / [资料] 格式。
"""
    else:
        body = f"{header}\n{context_block}\n{shared}"

    return body.strip()


# ---------------------------------------------------------------------------
# Figure planning
# ---------------------------------------------------------------------------

def build_figure_plan_prompt(markdown_content: str) -> str:
    return f"""
请根据下列课程学习内容，规划 2-6 张教学示意图。只返回 JSON 数组。
每个对象包含 title、caption、prompt、template、target_section 五个字段。
template 可选值：gauss_sphere, gauss_cylinder, image_plane, image_sphere, boundary, potential_field, knowledge_map

内容：
{markdown_content[:5000]}
""".strip()
