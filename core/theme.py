"""StudyPilot AI — Brand visual system.

Centralized color palette, typography, and CSS injection for Streamlit.
Design direction: cream paper, sage green accents, GoodNotes/Forest feel.
"""

from __future__ import annotations

import streamlit as st

# ── Colour palette ──────────────────────────────────────────────────────────
COLORS = {
    "background": "#F8F5EF",   # cream paper base
    "card": "#FFFDF8",          # warm white card surface
    "primary": "#7FA87A",      # sage green — buttons, links, emphasis
    "accent": "#A7C4A0",       # light sage — hover states, secondary
    "border": "#E6E0D6",       # warm grey — card borders, dividers
    "text": "#3B3B3B",         # charcoal — body copy
    "subtext": "#7A7A7A",      # warm grey — secondary text
    "warning": "#D6A85C",      # warm gold — caution / review
    "error": "#C56C6C",        # soft red — errors / draft
}

# ── CSS theme ───────────────────────────────────────────────────────────────
CSS_THEME = f"""
<style>
/* ---- global page background ---- */
.stApp {{
    background-color: {COLORS["background"]};
}}

/* ---- sidebar ---- */
[data-testid="stSidebar"] {{
    background-color: {COLORS["card"]};
    border-right: 1px solid {COLORS["border"]};
}}

[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {{
    color: {COLORS["text"]};
}}

/* ---- main content ---- */
.main .block-container {{
    padding-top: 2rem;
    max-width: 960px;
}}

/* ---- buttons ---- */
.stButton > button {{
    background-color: {COLORS["primary"]};
    color: #ffffff;
    border: none;
    border-radius: 16px;
    padding: 0.6rem 1.8rem;
    font-weight: 600;
    font-size: 0.95rem;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(127, 168, 122, 0.25);
}}

.stButton > button:hover {{
    background-color: {COLORS["accent"]};
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(127, 168, 122, 0.35);
}}

.stButton > button:active {{
    transform: translateY(0);
}}

/* secondary / outline button */
.stButton > button[kind="secondary"] {{
    background-color: transparent;
    color: {COLORS["primary"]};
    border: 1.5px solid {COLORS["primary"]};
    box-shadow: none;
}}

.stButton > button[kind="secondary"]:hover {{
    background-color: rgba(127, 168, 122, 0.08);
}}

/* ---- metric cards ---- */
[data-testid="stMetricValue"] {{
    color: {COLORS["primary"]};
    font-weight: 700;
}}

/* ---- progress bar ---- */
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, {COLORS["primary"]}, {COLORS["accent"]});
}}

/* ---- text inputs & text areas ---- */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    border-radius: 12px;
    border: 1.5px solid {COLORS["border"]};
    background-color: {COLORS["card"]};
    color: {COLORS["text"]};
}}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: {COLORS["primary"]};
    box-shadow: 0 0 0 3px rgba(127, 168, 122, 0.15);
}}

/* ---- select boxes ---- */
.stSelectbox > div > div {{
    border-radius: 12px;
}}

/* ---- expanders ---- */
.streamlit-expanderHeader {{
    border-radius: 12px;
    background-color: {COLORS["card"]};
    border: 1px solid {COLORS["border"]};
}}

/* ---- containers with border ---- */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: {COLORS["card"]};
    border-radius: 16px;
    border: 1px solid {COLORS["border"]};
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.09);
}}

/* ---- custom card class (injected via st.markdown) ---- */
.study-card {{
    background: {COLORS["card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    padding: 1.5rem;
    margin: 0.5rem 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.study-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.09);
}}

/* ---- hero banner ---- */
.hero-banner {{
    text-align: center;
    padding: 2rem 1rem 1.5rem;
}}

.hero-banner h1 {{
    color: {COLORS["text"]};
    font-size: 2.6rem;
    font-weight: 800;
    margin-bottom: 0.3rem;
}}

.hero-banner .brand-accent {{
    color: {COLORS["primary"]};
}}

.hero-banner .subtitle {{
    color: {COLORS["subtext"]};
    font-size: 1.05rem;
    line-height: 1.7;
    margin-top: 0.5rem;
}}

/* ---- quality badges ---- */
.quality-badge {{
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
}}

.quality-recommended {{
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #a5d6a7;
}}

.quality-review {{
    background: #fff8e1;
    color: #e65100;
    border: 1px solid #ffe082;
}}

.quality-draft {{
    background: #ffebee;
    color: #c62828;
    border: 1px solid #ef9a9a;
}}

/* ---- bunny mascot bubble ---- */
.bunny-bubble {{
    background: {COLORS["card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 16px;
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    font-size: 0.9rem;
    color: {COLORS["subtext"]};
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}}

/* ---- step indicator ---- */
.step-row {{
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin: 1rem 0 2rem;
    flex-wrap: wrap;
}}

.step-dot {{
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: {COLORS["border"]};
    display: inline-block;
}}

.step-dot.active {{
    background: {COLORS["primary"]};
}}

.step-dot.done {{
    background: {COLORS["accent"]};
}}

/* ---- footer ---- */
.footer-encourage {{
    text-align: center;
    color: {COLORS["subtext"]};
    font-size: 0.85rem;
    margin-top: 2rem;
    padding: 1.5rem 0;
    border-top: 1px solid {COLORS["border"]};
}}

/* ---- radio buttons as cards ---- */
.stRadio > div[role="radiogroup"] > label {{
    background: {COLORS["card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 0.6rem 1rem;
    margin: 0.25rem 0;
    transition: all 0.15s ease;
}}

.stRadio > div[role="radiogroup"] > label:hover {{
    border-color: {COLORS["primary"]};
    background: rgba(127, 168, 122, 0.04);
}}

/* ---- tabs ---- */
.stTabs [data-baseweb="tab"] {{
    border-radius: 12px 12px 0 0;
}}

/* ---- hr / divider ---- */
hr {{
    border-color: {COLORS["border"]};
    margin: 1.5rem 0;
}}

/* ---- file uploader ---- */
[data-testid="stFileUploader"] {{
    border-radius: 16px;
    border: 2px dashed {COLORS["border"]};
    background: {COLORS["card"]};
}}
</style>
"""


def inject_theme() -> None:
    """Inject the StudyPilot brand CSS into the Streamlit app.

    Call once at app startup, immediately after ``st.set_page_config()``.
    """
    st.markdown(CSS_THEME, unsafe_allow_html=True)
