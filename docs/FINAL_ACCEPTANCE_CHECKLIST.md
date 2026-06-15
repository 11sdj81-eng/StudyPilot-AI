# StudyPilot v1.3 — Final Acceptance Checklist

## UI & Flow

- [ ] `streamlit run app.py` 正常启动
- [ ] 首页 Hero 区显示正确标题和副标题
- [ ] 首页显示"今日学习状态"卡片（有 profile 时）或引导提示（无 profile 时）
- [ ] Agent 输入框 placeholder 显示示例目标文本
- [ ] 输入目标文本后点击"开始规划"正确跳转到 goal 页
- [ ] 首页显示 AI 理解结果（课程、时间、薄弱点、推荐模式）
- [ ] 学习路径图 expander 可展开，显示概念节点
- [ ] 薄弱点高亮为橙色边框 + "⚠️ 优先复习"标注
- [ ] Task cards（系统学习、考前冲刺、模拟考试、真题精讲）正常显示
- [ ] Sidebar 显示课程选择器、存储状态、近期生成、Bunny 提示
- [ ] Bunny 提示信息与用户画像关联（有 profile 时显示个性化消息）

## UserProfile & Personalization

- [ ] `data/user_profile/profile.json` 存在且可读写
- [ ] 输入"明天考电磁场，高斯定理不稳"后 profile 正确更新
- [ ] `PersonalizationEngine.build_plan()` 返回有效计划
- [ ] `build_today_card()` 区分有/无 profile 状态
- [ ] 考前冲刺场景正确识别（remaining_hours ≤ 3 或 remaining_days ≤ 1）
- [ ] 推荐输出正确（exam_sprint → Sprint + PastPaper）

## Wizard Flow

- [ ] Home → Goal → Upload → AI Recognition → Preferences → Progress → Results
- [ ] Goal 页显示解析结果
- [ ] 点击"确认目标"后 profile 持久化
- [ ] Preferences 页设置后 profile 更新（PDF 风格、插图偏好、真题驱动）
- [ ] 后台生成不阻塞 UI
- [ ] 生成完成后自动跳转到 Results 页

## Results Page

- [ ] 显示质量徽章
- [ ] 显示 PDF 页数、文件大小、质量分数
- [ ] "学习建议 & 覆盖率" expander 展开显示
- [ ] 显示建议学习顺序
- [ ] 显示本次资料覆盖的知识点
- [ ] 显示使用场景标签（Sprint/PastPaper/MockExam/Review）
- [ ] 显示 Bunny 个性化建议卡片
- [ ] 下载 PDF / Markdown 按钮正常工作
- [ ] 标记为 final 功能正常
- [ ] 重新生成和删除按钮正常

## Output Management

- [ ] `data/outputs/runs/` 目录结构正确
- [ ] run manifest 包含完整元数据
- [ ] `data/demo/demo_manifest.json` 成功生成
- [ ] 清理功能正常工作

## Documents

- [ ] `docs/PROJECT_SHOWCASE.md` 内容完整
- [ ] `docs/RESUME_BULLETS.md` 中英文描述完整
- [ ] `docs/ACKNOWLEDGEMENTS.md` 第三方状态准确
- [ ] `docs/THIRD_PARTY_NOTICES.md` 法律声明完整
- [ ] `docs/ARCHITECTURE_V5.md` 架构说明准确
- [ ] `README.md` 已更新

## PDF v4.1 Stability

- [ ] PDF v4.1 生成不受影响
- [ ] 未修改 Typst 模板
- [ ] 未修改 Figure Engine
- [ ] 未修改 DeepSeek 配置

## Known Issues (v1.3)

- [ ] 教材 PDF 为扫描版时，PyMuPDF 无法提取文本 → 标注为已知限制
- [ ] MinerU / PaddleOCR 不可用 → 文档中已说明原因
- [ ] DocLayout-YOLO 权重不可用 → 文档中已说明原因
- [ ] Marker 模型下载未完成 → 文档中已说明网络原因

---

*签名: ___________  日期: ___________*
