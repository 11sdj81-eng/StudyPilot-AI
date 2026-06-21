"""AI Tutor — single entry point for all user interactions.

LLM First: always try DeepSeek before falling back.
RAG is enhancement, not a gate.
Cross-course questions get answered, not rejected.
"""

from core.ai_tutor.orchestrator import AITutorOrchestrator, get_tutor
from core.ai_tutor.intent_router import IntentRouter, Intent, IntentResult
