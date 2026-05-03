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

mode = st.radio(
    "Simulation Mode",
    ["General CPI RV", "Medical CPI vs CPI Basis"],
    horizontal=True,
    key="simulation_mode_selector",
    help="Switch between the existing CPI relative-value simulation and the new medical-inflation-vs-CPI basis mode.",
)

if mode == "Medical CPI vs CPI Basis":
    render_medical_cpi_basis_sim_tab()
else:
    render_falconx_sim_tab()
