#!/bin/bash
# StudyPilot v5.2 — DI Worker environment setup
# Creates a Python 3.11 venv and installs dependencies step-by-step.
# Usage: bash setup_worker_env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv-di"
REPORT_DIR="$SCRIPT_DIR/../../data/outputs/v5_reports"
mkdir -p "$REPORT_DIR"

echo "========================================"
echo "StudyPilot DI Worker — Environment Setup"
echo "========================================"

# ---- Find Python 3.11 ----
PYTHON311=""
for candidate in python3.11 /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON311="$candidate"
        break
    fi
done

if [ -z "$PYTHON311" ]; then
    echo ""
    echo "❌ Python 3.11 not found."
    echo "   Install with one of:"
    echo "     brew install python@3.11"
    echo "     pyenv install 3.11"
    echo "     conda create -n di-worker python=3.11"
    echo "     uv python install 3.11"
    exit 1
fi

echo "✅ Python 3.11 found: $($PYTHON311 --version)"

# ---- Create venv ----
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment at $VENV_DIR ..."
    $PYTHON311 -m venv "$VENV_DIR"
    echo "✅ venv created"
else
    echo "✅ venv already exists at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ---- Upgrade pip ----
python -m pip install --upgrade pip -q

# ---- Step 1: Base dependencies (must succeed) ----
echo ""
echo "━━━ Step 1: Base dependencies ━━━"
python -m pip install pymupdf pillow opencv-python numpy python-pptx 2>&1 | tail -3
echo "✅ Base dependencies installed"

# ---- Step 2: PaddleOCR ----
echo ""
echo "━━━ Step 2: PaddleOCR ━━━"
PADDLE_OK=false
python -m pip install paddlepaddle 2>&1 | tail -3 || echo "⚠️  paddlepaddle install failed"
python -m pip install paddleocr 2>&1 | tail -3 || echo "⚠️  paddleocr install failed"
python -c "import paddleocr; print('PaddleOCR version:', paddleocr.__version__)" 2>/dev/null && PADDLE_OK=true || echo "⚠️  PaddleOCR import failed"
echo "PaddleOCR available: $PADDLE_OK"

# ---- Step 3: Marker ----
echo ""
echo "━━━ Step 3: Marker ━━━"
MARKER_OK=false
python -m pip install marker-pdf 2>&1 | tail -5 || echo "⚠️  marker-pdf install failed"
python -c "from marker.converters.pdf import PdfConverter; print('Marker OK')" 2>/dev/null && MARKER_OK=true || echo "⚠️  Marker import failed"
echo "Marker available: $MARKER_OK"

# ---- Step 4: MinerU ----
echo ""
echo "━━━ Step 4: MinerU ━━━"
MINERU_OK=false
python -m pip install magic-pdf 2>&1 | tail -5 || echo "⚠️  magic-pdf install failed"
python -c "import magic_pdf; print('MinerU OK')" 2>/dev/null && MINERU_OK=true || echo "⚠️  MinerU import failed"
echo "MinerU available: $MINERU_OK"

# ---- Step 5: DocLayout-YOLO ----
echo ""
echo "━━━ Step 5: DocLayout-YOLO ━━━"
DOCLAYOUT_OK=false
python -m pip install ultralytics doclayout-yolo 2>&1 | tail -3 || echo "⚠️  doclayout-yolo install failed"
python -c "import doclayout_yolo; print('DocLayout-YOLO OK')" 2>/dev/null && DOCLAYOUT_OK=true || echo "⚠️  DocLayout-YOLO import failed"
echo "DocLayout-YOLO available: $DOCLAYOUT_OK"

# ---- Generate report ----
python -c "
import json, sys
report = {
    'worker_python': sys.version,
    'venv_path': '$VENV_DIR',
    'dependencies': {
        'base': True,
        'paddleocr': $PADDLE_OK,
        'marker': $MARKER_OK,
        'mineru': $MINERU_OK,
        'doclayout_yolo': $DOCLAYOUT_OK,
    },
    'any_ocr_available': $PADDLE_OK or $MARKER_OK,
    'any_parser_available': $MARKER_OK or $MINERU_OK,
    'any_layout_available': $DOCLAYOUT_OK,
}
with open('$REPORT_DIR/worker_dependency_report.json', 'w') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps(report, indent=2))
"

echo ""
echo "========================================"
echo "Worker environment setup complete."
echo "Activate with: source $VENV_DIR/bin/activate"
echo "Report: $REPORT_DIR/worker_dependency_report.json"
echo "========================================"
