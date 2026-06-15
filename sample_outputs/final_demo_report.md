# StudyPilot v5.2 — Final Demo Report

**Generated:** 2026-06-15 16:07:28

## Demo Summary

- Course: 电磁场与电磁波
- Chapter: 第一章 静电场
- User Input: "明天考电磁场，我只有3小时，高斯定理和镜像法不稳，帮我安排复习。"

## OCR Results

| Source | Pages | Chars |
|--------|-------|-------|
| Textbook | 5 | 2459 |
| Exam | 5 | 3673 |
| **Total** | — | **6132** |

## Knowledge Extraction

- Concept evidence items: 16
- Unique concepts: 5
- Exam question candidates: 10

## Figure Status

- Precise crops: 3
- Programmatic fallbacks: 11
- Usable for PDF: 11

## Demo Files

- StudyPilot_v5_Review_RealDemo.md
- full_real_pipeline_report.json
- figure_status_report.json
- demo_manifest.json
- final_demo_report.md
- final_acceptance_report.md

## Demo Flow

1. Start `streamlit run app.py`
2. Enter "明天考电磁场，高斯定理和镜像法不稳"
3. View AI understanding + personalized plan
4. Upload textbook + exam PDFs
5. Generate Sprint + PastPaper
6. View results with study advice

## Known Limitations

- DocLayout-YOLO 权重不可用 → 无自动教材插图裁剪
- MinerU 已安装但未完整测试
- Marker 模型下载中 (一次性网络延迟)
- Typst CLI 需要 brew install typst 才能生成正式 PDF
