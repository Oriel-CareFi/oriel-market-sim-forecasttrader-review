"""
Oriel Market Simulation — CPI RV + Medical CPI Basis Pilot
Standalone Streamlit instance for ForecastTrader review.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Oriel Market Simulation — CPI RV + Medical CPI Basis",
    page_icon="\u25c8",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from ui.css import inject_css
inject_css()

# ── Password gate (ForecastTrader review build) ───────────────────────────────
# Per docs/deployments/forecasttrader_password_gated_review_deployment.md:
# the deployment is a public Streamlit app gated by an in-app password
# stored in Streamlit Secrets as `review_password`. The gate is activated
# by setting the Streamlit Secret `REVIEW_BUILD = "true"` on the deployed
# app — production deployments without that secret stay open.
#
# This must run BEFORE any data loading or tab rendering so unauthenticated
# users see only the password prompt and st.stop() halts the script.
from services.review_password_gate import (
    check_review_password,
    review_build_gate_enabled,
)

if review_build_gate_enabled() and not check_review_password():
    st.stop()

from falconx_sim_tab import render_falconx_sim_tab
from medical_cpi_basis_sim_tab import render_medical_cpi_basis_sim_tab

st.markdown("""
<div class='oriel-page-head'>
  <span class='oriel-page-title'>Oriel Market Simulation</span>
  <span class='version-chip'>CPI RV + Medical CPI Basis</span>
</div>""", unsafe_allow_html=True)

st.markdown(
    "<div style='font-size:0.75rem;color:#6b7f94;margin:4px 0 10px;'>"
    "Execution-intelligence console for CPI relative value and medical-inflation-vs-CPI basis trades. Live venue ingestion, dislocation analytics, backtest engine, and ScaleTrader-style templates.</div>",
    unsafe_allow_html=True,
)

# ── Simulation Mode selector (styled as a segmented control) ─────────────────
# We override Streamlit's default horizontal-radio look so the mode selector
# matches the app's gold-accent design language: dark pill container, hidden
# native radio circles, gold-tinted active option, muted inactive options.
st.markdown(
    """
    <style>
      /* Pill container around the two options */
      [data-testid="stRadio"] > div[role="radiogroup"] {
        flex-direction: row !important;
        gap: 4px !important;
        background: #0f1620 !important;
        border: 1px solid #2a3a52 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        display: inline-flex !important;
      }
      /* Each option becomes a button-like pill */
      [data-testid="stRadio"] label[data-baseweb="radio"] {
        padding: 9px 22px !important;
        border-radius: 7px !important;
        cursor: pointer !important;
        transition: background 0.18s, color 0.18s, border-color 0.18s, box-shadow 0.18s !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.04em !important;
        color: #8fa3b8 !important;
        margin: 0 !important;
        border: 1px solid transparent !important;
      }
      /* Hide the native radio circle */
      [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
      [data-testid="stRadio"] label[data-baseweb="radio"] [role="radio"] {
        display: none !important;
      }
      /* Hover state */
      [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        color: #E6EDF3 !important;
        background: rgba(212, 168, 90, 0.05) !important;
      }
      /* Active (selected) — gold accent */
      [data-testid="stRadio"] label[data-baseweb="radio"]:has(input[aria-checked="true"]),
      [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
        background: linear-gradient(135deg, rgba(212,168,90,0.18) 0%, rgba(212,168,90,0.08) 100%) !important;
        color: #D4A85A !important;
        border-color: rgba(212,168,90,0.35) !important;
        box-shadow: 0 1px 8px rgba(212,168,90,0.12), inset 0 1px 0 rgba(255,255,255,0.04) !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='font-size:0.62rem;color:#8fa3b8;letter-spacing:0.16em;"
    "text-transform:uppercase;margin:14px 0 8px;font-weight:500;'>"
    "Simulation Mode"
    "</div>",
    unsafe_allow_html=True,
)

mode = st.radio(
    "Simulation Mode",
    ["General CPI RV", "Medical CPI vs CPI Basis"],
    horizontal=True,
    key="simulation_mode_selector",
    label_visibility="collapsed",
    help="Switch between the existing CPI relative-value simulation and the new medical-inflation-vs-CPI basis mode.",
)

if mode == "Medical CPI vs CPI Basis":
    render_medical_cpi_basis_sim_tab()
else:
    render_falconx_sim_tab()
