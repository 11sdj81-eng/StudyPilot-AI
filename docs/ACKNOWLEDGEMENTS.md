# Acknowledgements — StudyPilot v5.1

StudyPilot v5.1 integrates several open-source document intelligence tools as
**optional adapters**.  None of these tools are distributed with StudyPilot;
they must be installed separately by the user.

## Document Intelligence Tools — Real Status (2026-06-15)

| Tool | Version Tested | Status on This System | License | Notes |
|------|---------------|----------------------|---------|-------|
| **MinerU** (magic-pdf) | latest | ❌ Not installed | Apache 2.0 | Blocked by Python 3.14 / PyO3 incompatibility (max PyO3 supports 3.13). Use MinerU online (https://mineru.net) or Docker image. |
| **Marker** (marker-pdf) | 1.10.2 | ✅ Installed | GPL-3.0 | Python API works. Requires ~1.3GB Surya OCR model download on first run. Tested on exam PDFs. |
| **PaddleOCR** | 3.7.0 | ❌ Not installed | Apache 2.0 | No PaddlePaddle wheel for macOS arm64. Use Google Colab (Linux x86_64) or EasyOCR as alternative. |
| **DocLayout-YOLO** | 0.0.4 | ⚠️ Package installed, model unavailable | Apache 2.0 | Package installs but pretrained weights (juliozhao/DocLayout-YOLO-DocStructBench) fail to download — GitHub releases API returns 404. Using ultralytics YOLOv8n as fallback (not document-specific). |
| **PyMuPDF** (fitz) | 1.27.2.3 | ✅ Installed | AGPL-3.0 | Primary text extraction fallback. Works reliably. |
| **ultralytics** | 8.4.67 | ✅ Installed | AGPL-3.0 | Required by DocLayout-YOLO. |
| **OpenCV** | 4.13.0 | ✅ Installed | Apache 2.0 | Used for image crop operations. |

## Python Version Note

This project runs on **Python 3.14.4** (macOS arm64, Apple M4).
Python 3.14 is very new and **several ML packages do not yet support it**:

- **Pydantic-core / PyO3** (required by MinerU): max supported = Python 3.13
- **PaddlePaddle** (required by PaddleOCR): no macOS arm64 wheels at all
- **DocLayout-YOLO pretrained weights**: GitHub release URL resolution bug

**Recommendation:** For full DI capability, use Python 3.10–3.12 via pyenv or conda.

## LLM Services

| Service | Status | Notes |
|---------|--------|-------|
| **DeepSeek** | ✅ Configured | Primary LLM. Not modified in v5.1. |
| **Anthropic Claude** | Available via Marker | Marker supports Claude as optional LLM service. |

## Core Libraries (Always Required)

PyTorch 2.12.0, Transformers 4.57.6, Pillow 10.4.0, NumPy 2.4.6, Jinja2, Streamlit.

## License Compliance

Model weights are **not** distributed with this repository. Users download them at runtime from their respective sources. Users are responsible for verifying license compliance.

- **GPL-3.0** (Marker, PyMuPDF, ultralytics): Distribution may need GPL-3.0 compliance.
- **AGPL-3.0** (PyMuPDF): Network-use provisions may apply.
- **Apache 2.0** (MinerU, PaddleOCR, DocLayout-YOLO, OpenCV): Permissive.

---

*Generated: 2026-06-15 for StudyPilot v5.1*
