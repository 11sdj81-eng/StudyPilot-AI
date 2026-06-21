"""Similarity computation for question deduplication."""

from __future__ import annotations

import re
from collections import Counter

from core.pdf_content_v2.question_dedup.question_fingerprint import (
    DuplicateLevel, QuestionFingerprint,
)


def compute_similarity(fp1: QuestionFingerprint, fp2: QuestionFingerprint) -> tuple[DuplicateLevel | None, float]:
    """Compute the similarity level and score between two fingerprints.

    Returns (level, score) where level is the highest detected duplicate level,
    or None if not similar enough.
    """
    # Level 1: Exact duplicate
    if fp1.raw_text == fp2.raw_text and fp1.raw_text:
        return DuplicateLevel.EXACT, 1.0

    # Level 2: Normalized duplicate (same after number/variable removal)
    if fp1.normalized_text_hash == fp2.normalized_text_hash:
        return DuplicateLevel.NORMALIZED, 0.98

    # Also check normalized text similarity for near-exact matches
    norm_sim = _jaccard_similarity(
        _tokenize(fp1.normalized_text), _tokenize(fp2.normalized_text)
    )
    if norm_sim > 0.9:
        return DuplicateLevel.NORMALIZED, norm_sim

    # Level 3: Pattern duplicate (same concept + method + type)
    if fp1.pattern_key() == fp2.pattern_key() and fp1.pattern_key() != "unknown|unknown|unknown":
        # Check knowledge tag overlap
        tag_overlap = len(set(fp1.knowledge_tags) & set(fp2.knowledge_tags))
        tag_score = tag_overlap / max(1, len(set(fp1.knowledge_tags) | set(fp2.knowledge_tags)))
        # Check difficulty proximity
        diff_close = abs(fp1.difficulty - fp2.difficulty) <= 1
        if tag_score > 0.3 or diff_close:
            return DuplicateLevel.PATTERN, 0.75 + 0.1 * tag_score

    # Level 4: Semantic duplicate (keyword overlap + structure similarity)
    sem_sim = _keyword_similarity(fp1.raw_text, fp2.raw_text)
    if sem_sim > 0.85:
        return DuplicateLevel.SEMANTIC, sem_sim

    return None, 0.0


def _tokenize(text: str) -> list[str]:
    """Tokenize Chinese + English text."""
    # Split on spaces and punctuation
    tokens = re.findall(r'[一-鿿]+|[a-zA-Z]+|\{VAR\}|\{N\}', text.lower())
    return [t for t in tokens if len(t) > 1]


def _jaccard_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """Jaccard similarity between two token lists."""
    set1, set2 = set(tokens1), set(tokens2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def _keyword_similarity(text1: str, text2: str) -> float:
    """Chinese keyword overlap similarity."""
    # Extract 2-4 char Chinese substrings as keyword proxies
    def keywords(text: str) -> set:
        chars = re.findall(r'[一-鿿]{2,4}', text)
        return set(chars)

    kw1, kw2 = keywords(text1), keywords(text2)
    if not kw1 or not kw2:
        return 0.0
    # Weighted: both Jaccard and containment
    jaccard = len(kw1 & kw2) / len(kw1 | kw2)
    containment = len(kw1 & kw2) / min(len(kw1), len(kw2))
    return 0.6 * jaccard + 0.4 * containment


def diversity_score(fingerprints: list[QuestionFingerprint]) -> float:
    """Compute question diversity score (0-100).

    Dimensions:
        - Concept coverage: unique concepts / total
        - Difficulty spread: std deviation of difficulties
        - Question type variety: unique types / total
        - Method variety: unique methods / total
    """
    if not fingerprints:
        return 0.0

    n = len(fingerprints)

    concepts = {fp.concept_id for fp in fingerprints if fp.concept_id != "unknown"}
    types = {fp.question_type for fp in fingerprints if fp.question_type}
    methods = {fp.solution_method for fp in fingerprints if fp.solution_method != "unknown"}
    difficulties = [fp.difficulty for fp in fingerprints]

    # Concept coverage (normalize: expect at least 4 unique concepts)
    concept_score = min(1.0, len(concepts) / max(4, n * 0.5)) * 30

    # Type variety (expect at least 3 types: choice, fill, calculation)
    type_score = min(1.0, len(types) / 3) * 25

    # Method variety (expect at least 3 methods)
    method_score = min(1.0, len(methods) / 3) * 20

    # Difficulty spread
    if len(difficulties) >= 2:
        mean_d = sum(difficulties) / len(difficulties)
        var_d = sum((d - mean_d) ** 2 for d in difficulties) / len(difficulties)
        std_d = var_d ** 0.5
        diff_score = min(1.0, std_d / 1.5) * 15  # std≈1.5 is good spread
    else:
        diff_score = 5

    # Bonus for no duplicates detected
    dedup_bonus = 10  # base; will be reduced per duplicate found

    return concept_score + type_score + method_score + diff_score + dedup_bonus
