# Third-Party Notices — StudyPilot v5.1

## Software Components

Each third-party component is subject to its own license terms. StudyPilot does
not bundle any third-party code or model weights — all are installed separately
by the user via pip or equivalent.

### MinerU (magic-pdf)
- **Repository:** https://github.com/opendatalab/MinerU
- **License:** Apache License 2.0
- **Copyright:** OpenDataLab
- **Actual Status (2026-06-15):** NOT installed. Python 3.14 incompatible (PyO3 max 3.13). External tool mode reserved.

### Marker
- **Repository:** https://github.com/VikParuchuri/marker
- **License:** GPL-3.0
- **Copyright:** Vik Paruchuri
- **Actual Status (2026-06-15):** Installed (v1.10.2). Functional Python API. Model download required on first use.

### PaddleOCR
- **Repository:** https://github.com/PaddlePaddle/PaddleOCR
- **License:** Apache License 2.0
- **Copyright:** PaddlePaddle Authors
- **Actual Status (2026-06-15):** NOT installed. No PaddlePaddle wheel for macOS arm64.

### DocLayout-YOLO
- **Repository:** https://github.com/opendatalab/DocLayout-YOLO
- **License:** Apache License 2.0
- **Copyright:** OpenDataLab
- **Actual Status (2026-06-15):** Package installed (v0.0.4), model weights NOT downloadable (GitHub API 404).

### PyMuPDF
- **Repository:** https://github.com/pymupdf/PyMuPDF
- **License:** AGPL-3.0
- **Copyright:** Artifex Software, Inc.
- **Actual Status (2026-06-15):** Installed (v1.27.2.3). Core dependency.

### Ultralytics YOLO
- **Repository:** https://github.com/ultralytics/ultralytics
- **License:** AGPL-3.0
- **Copyright:** Ultralytics
- **Actual Status (2026-06-15):** Installed (v8.4.67).

### OpenCV
- **Repository:** https://github.com/opencv/opencv
- **License:** Apache License 2.0
- **Copyright:** OpenCV Foundation
- **Actual Status (2026-06-15):** Installed (v4.13.0).

## Model Weights

No pre-trained model weights are distributed with this repository. Models are
downloaded at runtime from their respective sources:

- Surya OCR model (~1.3 GB) — downloaded by Marker on first use
- DocLayout-YOLO weights — from Hugging Face Hub (currently inaccessible via doclayout_yolo package)
- YOLOv8 weights — downloaded by ultralytics on first use

## No Warranty

All third-party components are provided "as is", without warranty of any kind.

---

*Generated: 2026-06-15*
