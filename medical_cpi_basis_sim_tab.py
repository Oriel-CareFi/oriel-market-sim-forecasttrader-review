"""
medical_cpi_basis_sim_tab.py

Integrated Mode 2 for the Oriel Market Simulation review app.

Mode 2: Medical CPI vs. CPI Basis Simulation
- Demonstrates a parallel execution-intelligence workflow for a future
  medical-inflation-vs-headline-CPI basis contract.
- Intended for ForecastEx / ForecastTrader review builds.
- Uses transparent, adjustable assumptions and sample/synthetic simulation logic.
- Not production trading infrastructure.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.charts import _layout, _xaxis, _yaxis
from ui.plotly_theme import PLOTLY_CONFIG
from ui.tables import _plotly_desk_table
from ui.tokens import (
    BG_ELEVATED,
    DESK_TABLE_HEADER_PX,
    DESK_TABLE_PAD_PX,
    DESK_TABLE_ROW_PX,
    GOLD,
    NEGATIVE,
    POSITIVE,
    SERIES2,
    SERIES_MUTE,
    TEXT_MUTED,
    TEXT_SEC,
    WARNING,
)


@dataclass(frozen=True)
class MedicalCpiBasisInputs:
    """Inputs for the medical-inflation-vs-CPI basis simulation.

    Rate inputs are decimals: 0.041 = 4.10%.
    Volatility and threshold inputs are basis points.
    """

    headline_cpi_yoy: float
    hospital_services_yoy: float
    physician_services_yoy: float
    prescription_drugs_yoy: float
    other_medical_yoy: float

    hospital_weight: float
    physician_weight: float
    prescription_weight: float
    other_weight: float

    threshold_bps: float
    market_yes_price: float
    spread_vol_bps: float
    confidence_score: float
    liquidity_score: float
    max_position_contracts: int
    clip_size_contracts: int
    starting_inventory_contracts: int
    contract_multiplier: float = 1.0


@dataclass(frozen=True)
class MedicalCpiBasisResults:
    medical_cpi_yoy: float
    headline_cpi_yoy: float
    basis_bps: float
    threshold_bps: float
    fair_yes_probability: float
    market_yes_price: float
    edge_probability_points: float
    expected_value_per_contract: float
    expected_value_total_clip: float
    liquidity_grade: str
    signal_label: str
    disable_reason: str | None


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def _normalize_weights(weights: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    total = sum(weights)
    if total <= 0:
        return 0.30, 0.20, 0.15, 0.35
    return tuple(w / total for w in weights)


def _score_color(score: float) -> str:
    if score >= 0.70:
        return POSITIVE
    if score >= 0.50:
        return WARNING
    return NEGATIVE


def _signal_color(signal: str) -> str:
    if signal == "BUY YES":
        return POSITIVE
    if signal == "SELL / AVOID YES":
        return NEGATIVE
    return WARNING


def _fmt_money(v: float) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"


def grade_liquidity(score: float) -> str:
    if score >= 0.85:
        return "A"
    if score >= 0.70:
        return "B"
    if score >= 0.55:
        return "C"
    return "D"


def compute_weighted_medical_cpi_yoy(inputs: MedicalCpiBasisInputs) -> float:
    """Compute a transparent weighted medical CPI proxy from subcomponents."""

    weights = _normalize_weights(
        (
            inputs.hospital_weight,
            inputs.physician_weight,
            inputs.prescription_weight,
            inputs.other_weight,
        )
    )
    components = (
        inputs.hospital_services_yoy,
        inputs.physician_services_yoy,
        inputs.prescription_drugs_yoy,
        inputs.other_medical_yoy,
    )
    return float(sum(w * r for w, r in zip(weights, components)))


def compute_medical_cpi_basis_results(inputs: MedicalCpiBasisInputs) -> MedicalCpiBasisResults:
    """Compute fair value, edge, and trading-signal diagnostics for Mode 2."""

    medical_yoy = compute_weighted_medical_cpi_yoy(inputs)
    basis_bps = (medical_yoy - inputs.headline_cpi_yoy) * 10_000.0

    # Illustrative binary contract:
    # YES pays $1 if medical inflation minus headline CPI exceeds threshold.
    # Terminal spread is modeled as normal around the Oriel-implied basis.
    vol = max(inputs.spread_vol_bps, 1.0)
    z_score = (basis_bps - inputs.threshold_bps) / vol
    fair_prob = float(np.clip(_normal_cdf(z_score), 0.0, 1.0))

    edge_pp = (fair_prob - inputs.market_yes_price) * 100.0
    ev_per_contract = (fair_prob - inputs.market_yes_price) * inputs.contract_multiplier
    ev_total_clip = ev_per_contract * inputs.clip_size_contracts

    liquidity_grade = grade_liquidity(inputs.liquidity_score)

    if edge_pp >= 6.0 and inputs.confidence_score >= 0.75 and inputs.liquidity_score >= 0.65:
        signal = "BUY YES"
        disable_reason = None
    elif edge_pp <= -6.0 and inputs.confidence_score >= 0.75 and inputs.liquidity_score >= 0.65:
        signal = "SELL / AVOID YES"
        disable_reason = None
    else:
        signal = "WATCH"
        disable_reason = "Disable if edge < 6 pts, confidence < 75%, or liquidity < 65%."

    return MedicalCpiBasisResults(
        medical_cpi_yoy=medical_yoy,
        headline_cpi_yoy=inputs.headline_cpi_yoy,
        basis_bps=basis_bps,
        threshold_bps=inputs.threshold_bps,
        fair_yes_probability=fair_prob,
        market_yes_price=inputs.market_yes_price,
        edge_probability_points=edge_pp,
        expected_value_per_contract=ev_per_contract,
        expected_value_total_clip=ev_total_clip,
        liquidity_grade=liquidity_grade,
        signal_label=signal,
        disable_reason=disable_reason,
    )


def simulate_basis_paths(
    inputs: MedicalCpiBasisInputs,
    n_paths: int = 2_000,
    horizon_months: int = 6,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate illustrative mean-reverting basis paths in basis points."""

    rng = np.random.default_rng(seed)
    results = compute_medical_cpi_basis_results(inputs)

    horizon_months = max(1, int(horizon_months))
    n_paths = max(100, int(n_paths))

    monthly_vol = max(inputs.spread_vol_bps, 1.0) / sqrt(12.0)
    mean_level = results.basis_bps
    kappa = 0.18

    paths = np.zeros((horizon_months + 1, n_paths))
    paths[0, :] = results.basis_bps

    for t in range(1, horizon_months + 1):
        shock = rng.normal(0.0, monthly_vol, size=n_paths)
        drift = kappa * (mean_level - paths[t - 1, :])
        paths[t, :] = paths[t - 1, :] + drift + shock

    df = pd.DataFrame(paths)
    df.insert(0, "month", range(horizon_months + 1))
    return df


def summarize_path_distribution(path_df: pd.DataFrame, threshold_bps: float) -> pd.DataFrame:
    """Summarize path distribution for chart/table output."""

    path_values = path_df.drop(columns=["month"]).to_numpy()
    return pd.DataFrame(
        {
            "month": path_df["month"],
            "p10_bps": np.percentile(path_values, 10, axis=1),
            "p50_bps": np.percentile(path_values, 50, axis=1),
            "p90_bps": np.percentile(path_values, 90, axis=1),
            "prob_above_threshold": (path_values > threshold_bps).mean(axis=1),
        }
    )


def create_scaletrader_basis_template(
    inputs: MedicalCpiBasisInputs,
    results: MedicalCpiBasisResults,
) -> Dict[str, object]:
    """Create an illustrative ScaleTrader-style ticket for the basis contract."""

    start_price = float(np.clip(inputs.market_yes_price, 0.01, 0.99))
    if results.signal_label == "BUY YES":
        side = "Buy YES"
        increment = 0.01
        profit_taker = min(start_price + 0.03, 0.99)
    elif results.signal_label == "SELL / AVOID YES":
        side = "Sell / avoid YES"
        increment = -0.01
        profit_taker = max(start_price - 0.03, 0.01)
    else:
        side = "Watch / no ticket"
        increment = 0.00
        profit_taker = None

    levels = int(np.clip(abs(results.edge_probability_points) // 2, 3, 10))

    return {
        "Contract": f"Medical CPI YoY − CPI-U YoY > {inputs.threshold_bps:.0f} bps",
        "Side": side,
        "Start price": f"${start_price:.2f}",
        "Increment": f"{increment:+.2f}",
        "Levels": levels,
        "Clip size": f"{inputs.clip_size_contracts:,} contracts",
        "Max position": f"{inputs.max_position_contracts:,} contracts",
        "Starting inventory": f"{inputs.starting_inventory_contracts:,} contracts",
        "Profit-taker": "N/A" if profit_taker is None else f"${profit_taker:.2f}",
        "Disable conditions": (
            "Disable if edge < 6 pts, confidence < 75%, liquidity < 65%, "
            "or inventory exceeds approved limit."
        ),
    }


def _render_mode2_scaletrader_card(inputs: MedicalCpiBasisInputs, results: MedicalCpiBasisResults) -> None:
    ticket = create_scaletrader_basis_template(inputs, results)
    side_col = _signal_color(results.signal_label)

    pt = ticket["Profit-taker"]
    st.markdown(
        f"""
        <div class='kpi-strip-wrap' style='margin-top:4px;margin-bottom:14px'>
          <div class='kpi-strip-ribbon'>ILLUSTRATIVE SCALETRADER BASIS TICKET · NOT ROUTED · MEDICAL CPI VS CPI</div>
          <div class='kpi-strip' style='display:grid;grid-template-columns:repeat(8,minmax(0,1fr))'>
            <div class='kpi-cell'><div class='kpi-micro'>Side</div><div class='kpi-value kpi-value--lead' style='color:{side_col};font-size:1.18rem;'>{ticket['Side']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Start Price</div><div class='kpi-value'>{ticket['Start price']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Increment</div><div class='kpi-value'>{ticket['Increment']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Levels</div><div class='kpi-value'>{ticket['Levels']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Clip Size</div><div class='kpi-value'>{ticket['Clip size']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Max Position</div><div class='kpi-value'>{ticket['Max position']}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Profit-Taker</div><div class='kpi-value'>{pt}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Oriel Edge</div><div class='kpi-value'>{results.edge_probability_points:+.1f}<span style='font-size:0.68em;color:{TEXT_MUTED};font-weight:500;margin-left:3px;'>pp</span></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='note-box' style='margin-top:10px;'>"
        f"<div class='kpi-micro'>Disable Conditions</div>"
        f"<span style='color:{TEXT_SEC};font-size:0.74rem;line-height:1.55;'>"
        f"{ticket['Disable conditions']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_input_panel() -> tuple[MedicalCpiBasisInputs, int, int]:
    left, right = st.columns([1.05, 1], gap="medium")

    with left:
        st.markdown("<div class='shdr'>CPI + Medical CPI Assumptions</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:0.69rem;color:{TEXT_MUTED};margin:-2px 0 10px;'>"
            "Default values are illustrative. Replace with Oriel/BLS-derived current values as available.</div>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2, gap="medium")
        with c1:
            headline = st.number_input("Headline CPI-U YoY (%)", -5.0, 20.0, 3.20, 0.10, key="m2_headline")
            hospital = st.number_input("Hospital services YoY (%)", -10.0, 30.0, 5.80, 0.10, key="m2_hospital")
            physician = st.number_input("Physician services YoY (%)", -10.0, 30.0, 4.70, 0.10, key="m2_physician")
        with c2:
            rx = st.number_input("Prescription drugs YoY (%)", -10.0, 30.0, 3.90, 0.10, key="m2_rx")
            other = st.number_input("Other medical components YoY (%)", -10.0, 30.0, 4.20, 0.10, key="m2_other")

        st.markdown("<div class='shdr' style='margin-top:14px;'>Medical CPI Proxy Weights</div>", unsafe_allow_html=True)
        w1, w2 = st.columns(2, gap="medium")
        with w1:
            hospital_w = st.slider("Hospital services", 0.0, 1.0, 0.30, 0.01, key="m2_w_hospital")
            physician_w = st.slider("Physician services", 0.0, 1.0, 0.20, 0.01, key="m2_w_physician")
        with w2:
            rx_w = st.slider("Prescription drugs", 0.0, 1.0, 0.15, 0.01, key="m2_w_rx")
            other_w = st.slider("Other medical", 0.0, 1.0, 0.35, 0.01, key="m2_w_other")

    with right:
        st.markdown("<div class='shdr'>Contract + Market Assumptions</div>", unsafe_allow_html=True)
        threshold = st.number_input(
            "Basis threshold: Medical CPI minus CPI-U (bps)",
            -500.0,
            1500.0,
            100.0,
            25.0,
            key="m2_threshold",
            help="YES pays if medical CPI outperforms headline CPI by more than this threshold.",
        )
        market_yes = st.slider("Market YES price", 0.01, 0.99, 0.42, 0.01, key="m2_market_yes")
        spread_vol = st.slider("Basis spread volatility (bps)", 25.0, 500.0, 175.0, 5.0, key="m2_spread_vol")

        q1, q2 = st.columns(2, gap="medium")
        with q1:
            confidence = st.slider("Confidence score", 0.0, 1.0, 0.82, 0.01, key="m2_conf")
            clip = st.number_input("Clip size", 1, 100_000, 250, 50, key="m2_clip")
        with q2:
            liquidity = st.slider("Liquidity score", 0.0, 1.0, 0.74, 0.01, key="m2_liq")
            max_pos = st.number_input("Max position", 1, 1_000_000, 2_000, 100, key="m2_maxpos")

        starting_inventory = st.number_input(
            "Starting inventory",
            -1_000_000,
            1_000_000,
            0,
            100,
            key="m2_start_inv",
        )
        horizon = st.slider("Simulation horizon (months)", 1, 24, 6, 1, key="m2_horizon")
        paths = st.slider("Number of simulated paths", 250, 10_000, 2_000, 250, key="m2_paths")

    inputs = MedicalCpiBasisInputs(
        headline_cpi_yoy=headline / 100.0,
        hospital_services_yoy=hospital / 100.0,
        physician_services_yoy=physician / 100.0,
        prescription_drugs_yoy=rx / 100.0,
        other_medical_yoy=other / 100.0,
        hospital_weight=hospital_w,
        physician_weight=physician_w,
        prescription_weight=rx_w,
        other_weight=other_w,
        threshold_bps=threshold,
        market_yes_price=market_yes,
        spread_vol_bps=spread_vol,
        confidence_score=confidence,
        liquidity_score=liquidity,
        max_position_contracts=int(max_pos),
        clip_size_contracts=int(clip),
        starting_inventory_contracts=int(starting_inventory),
    )
    return inputs, int(horizon), int(paths)


def _basis_distribution_fig(summary_df: pd.DataFrame, threshold_bps: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=summary_df["month"],
            y=summary_df["p90_bps"],
            mode="lines",
            line=dict(color=SERIES2, width=1),
            name="P90",
            hovertemplate="Month %{x}<br>P90: %{y:.0f} bp<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary_df["month"],
            y=summary_df["p10_bps"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(122,162,247,0.16)",
            line=dict(color=SERIES2, width=1),
            name="P10-P90",
            hovertemplate="Month %{x}<br>P10: %{y:.0f} bp<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary_df["month"],
            y=summary_df["p50_bps"],
            mode="lines+markers",
            line=dict(color=GOLD, width=2.5),
            marker=dict(color=GOLD, size=6),
            name="Median basis",
            hovertemplate="Month %{x}<br>Median: %{y:.0f} bp<extra></extra>",
        )
    )
    fig.add_hline(y=threshold_bps, line_color=WARNING, line_dash="dash", line_width=1)
    fig.update_layout(
        **_layout(
            height=340,
            margin=dict(l=78, r=44, t=32, b=72),
            xaxis=_xaxis(title=dict(text="Month", font=dict(color=TEXT_SEC, size=11), standoff=14), automargin=True),
            yaxis=_yaxis(title=dict(text="Medical CPI basis (bp)", font=dict(color=TEXT_SEC, size=11), standoff=14), automargin=True),
        )
    )
    return fig


def _threshold_probability_fig(summary_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=summary_df["month"],
            y=summary_df["prob_above_threshold"] * 100.0,
            mode="lines+markers",
            line=dict(color=POSITIVE, width=2.5),
            marker=dict(color=POSITIVE, size=6),
            name="Probability above threshold",
            hovertemplate="Month %{x}<br>Prob: %{y:.1f}%<extra></extra>",
        )
    )
    fig.update_layout(
        **_layout(
            height=340,
            margin=dict(l=78, r=44, t=32, b=72),
            xaxis=_xaxis(title=dict(text="Month", font=dict(color=TEXT_SEC, size=11), standoff=14), automargin=True),
            yaxis=_yaxis(title=dict(text="Probability (%)", font=dict(color=TEXT_SEC, size=11), standoff=14), automargin=True),
        )
    )
    fig.update_yaxes(range=[0, 100])
    return fig


def render_medical_cpi_basis_sim_tab() -> None:
    """Render the fully integrated Medical CPI vs CPI Basis simulation mode."""

    st.markdown(
        """
        <div style='font-size:0.69rem;color:#8EA4B5;margin:6px 0 12px;line-height:1.55;'>
        <b style='color:#B0BEC9;'>Mode 2: Medical CPI vs. CPI Basis.</b>
        This review mode shows how the same execution-intelligence workflow used for CPI relative value can extend into a healthcare-specific basis contract:
        <span style='color:#D4A85A;'>Medical CPI YoY − Headline CPI-U YoY &gt; threshold</span>.
        It is illustrative and not production trading infrastructure.
        </div>
        """,
        unsafe_allow_html=True,
    )

    inputs, horizon_months, n_paths = _render_input_panel()
    results = compute_medical_cpi_basis_results(inputs)

    signal_col = _signal_color(results.signal_label)
    conf_col = _score_color(inputs.confidence_score)
    liq_col = _score_color(inputs.liquidity_score)
    ev_col = POSITIVE if results.expected_value_total_clip >= 0 else NEGATIVE

    st.markdown(
        f"""
        <div class='kpi-strip-wrap' style='margin:16px 0 10px'>
          <div class='kpi-strip-ribbon'>MEDICAL CPI BASIS SIGNAL · THRESHOLD {results.threshold_bps:.0f} BP · MARKET YES ${results.market_yes_price:.2f}</div>
          <div class='kpi-strip' style='display:grid;grid-template-columns:repeat(8,minmax(0,1fr))'>
            <div class='kpi-cell'><div class='kpi-micro'>Medical CPI Proxy</div><div class='kpi-value'>{results.medical_cpi_yoy*100:.2f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>%</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Headline CPI-U</div><div class='kpi-value'>{results.headline_cpi_yoy*100:.2f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>%</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Basis</div><div class='kpi-value kpi-value--lead' style='color:{GOLD};'>{results.basis_bps:.0f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>bp</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Fair YES</div><div class='kpi-value'>{results.fair_yes_probability*100:.1f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>%</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Edge vs Market</div><div class='kpi-value' style='color:{signal_col};'>{results.edge_probability_points:+.1f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>pp</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Confidence</div><div class='kpi-value' style='color:{conf_col};'>{inputs.confidence_score:.0%}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Liquidity</div><div class='kpi-value' style='color:{liq_col};'>{results.liquidity_grade}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Signal</div><div class='kpi-value' style='color:{signal_col};font-size:1.05rem;'>{results.signal_label}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if results.disable_reason:
        st.warning(results.disable_reason)
    else:
        st.success("Signal passes illustrative edge, confidence, and liquidity gates.")

    path_df = simulate_basis_paths(inputs, n_paths=n_paths, horizon_months=horizon_months)
    summary_df = summarize_path_distribution(path_df, inputs.threshold_bps)

    col_l, col_r = st.columns([1.1, 1], gap="medium")
    with col_l:
        st.markdown("<div class='shdr'>Simulated Medical CPI Basis Distribution</div>", unsafe_allow_html=True)
        st.plotly_chart(
            _basis_distribution_fig(summary_df, inputs.threshold_bps),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            theme=None,
            key="m2_basis_distribution",
        )
    with col_r:
        st.markdown("<div class='shdr'>Probability Above Threshold</div>", unsafe_allow_html=True)
        st.plotly_chart(
            _threshold_probability_fig(summary_df),
            use_container_width=True,
            config=PLOTLY_CONFIG,
            theme=None,
            key="m2_prob_above_threshold",
        )

    st.markdown("<div class='shdr oriel-section-gap'>Illustrative ScaleTrader Basis Ticket — Not Routed</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.69rem;color:{TEXT_MUTED};margin:-2px 0 8px;'>"
        "Demo-only translation layer for a future medical-inflation-vs-CPI basis contract. "
        "No IBKR authentication, TWS routing, or live order submission is wired in.</div>",
        unsafe_allow_html=True,
    )
    _render_mode2_scaletrader_card(inputs, results)

    st.markdown("<div class='shdr oriel-section-gap'>PnL / EV Diagnostics</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='kpi-strip-wrap' style='margin-bottom:12px'>
          <div class='kpi-strip-ribbon'>EXPECTED VALUE · CLIP {inputs.clip_size_contracts:,} CONTRACTS · MAX POSITION {inputs.max_position_contracts:,}</div>
          <div class='kpi-strip' style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr))'>
            <div class='kpi-cell'><div class='kpi-micro'>EV / Contract</div><div class='kpi-value' style='color:{ev_col};'>{_fmt_money(results.expected_value_per_contract)}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>EV / Clip</div><div class='kpi-value kpi-value--lead' style='color:{ev_col};'>{_fmt_money(results.expected_value_total_clip)}</div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Inventory Utilization</div><div class='kpi-value'>{abs(inputs.starting_inventory_contracts)/max(inputs.max_position_contracts, 1)*100:.1f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>%</span></div></div>
            <div class='kpi-cell'><div class='kpi-micro'>Spread Vol</div><div class='kpi-value'>{inputs.spread_vol_bps:.0f}<span style='font-size:0.68em;color:{TEXT_MUTED};margin-left:3px;'>bp</span></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_show = summary_df.copy()
    summary_show["p10_bps"] = summary_show["p10_bps"].map(lambda x: f"{x:,.0f}")
    summary_show["p50_bps"] = summary_show["p50_bps"].map(lambda x: f"{x:,.0f}")
    summary_show["p90_bps"] = summary_show["p90_bps"].map(lambda x: f"{x:,.0f}")
    summary_show["prob_above_threshold"] = summary_show["prob_above_threshold"].map(lambda x: f"{x*100:.1f}%")
    summary_show = summary_show.rename(
        columns={
            "month": "Month",
            "p10_bps": "P10 Basis",
            "p50_bps": "Median Basis",
            "p90_bps": "P90 Basis",
            "prob_above_threshold": "Pr(Above Threshold)",
        }
    )
    tfig = _plotly_desk_table(summary_show, gold_column="Pr(Above Threshold)")
    content_h = DESK_TABLE_HEADER_PX + len(summary_show) * DESK_TABLE_ROW_PX + DESK_TABLE_PAD_PX
    viewport_h = DESK_TABLE_HEADER_PX + min(len(summary_show), 7) * DESK_TABLE_ROW_PX + DESK_TABLE_PAD_PX
    tfig.update_layout(height=content_h)
    st.markdown("<div class='shdr oriel-section-gap'>Path Summary</div>", unsafe_allow_html=True)
    with st.container(height=viewport_h, border=False, key="scroll_m2_path_summary"):
        st.plotly_chart(tfig, use_container_width=True, config=PLOTLY_CONFIG, theme=None, key="m2_path_summary_tbl")

    st.markdown(
        f"<div style='font-size:0.68rem;color:{TEXT_MUTED};margin-top:8px;'>"
        "Mode 2 is intentionally lightweight: it proves the execution-intelligence pattern for a medical CPI basis market without hard-wiring claims, CMS lag, or production medical-CPI curve infrastructure. "
        "CPI proves the workflow; medical CPI basis is the differentiated expansion path.</div>",
        unsafe_allow_html=True,
    )
