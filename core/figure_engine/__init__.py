"""StudyPilot Figure Engine v1.0 —— 教材/PPT/真题图像检索与教学插图系统.

Provides:
- PDF/PPTX image extraction
- FigureBank asset management
- Concept matching & ranking
- Best-figure selection with fallback
- Quality gate & reporting
"""

from core.figure_engine.figure_objects import FigureObject, SourceType, ConceptId
from core.figure_engine.figure_bank import FigureBank
from core.figure_engine.figure_matcher import FigureMatcher
from core.figure_engine.figure_ranker import FigureRanker
from core.figure_engine.figure_selector import FigureSelector
from core.figure_engine.figure_rewriter import FigureRewriter
from core.figure_engine.figure_quality_gate import FigureQualityGate
from core.figure_engine.figure_engine_report import FigureEngineReport
from core.figure_engine.pdf_figure_extractor import PdfFigureExtractor
from core.figure_engine.ppt_figure_extractor import PptFigureExtractor
