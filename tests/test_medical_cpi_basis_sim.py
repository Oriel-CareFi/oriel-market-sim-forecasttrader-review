from medical_cpi_basis_sim_tab import (
    MedicalCpiBasisInputs,
    compute_medical_cpi_basis_results,
    simulate_basis_paths,
    summarize_path_distribution,
    create_scaletrader_basis_template,
)


def sample_inputs():
    return MedicalCpiBasisInputs(
        headline_cpi_yoy=0.032,
        hospital_services_yoy=0.058,
        physician_services_yoy=0.047,
        prescription_drugs_yoy=0.039,
        other_medical_yoy=0.042,
        hospital_weight=0.30,
        physician_weight=0.20,
        prescription_weight=0.15,
        other_weight=0.35,
        threshold_bps=100.0,
        market_yes_price=0.42,
        spread_vol_bps=175.0,
        confidence_score=0.82,
        liquidity_score=0.74,
        max_position_contracts=2000,
        clip_size_contracts=250,
        starting_inventory_contracts=0,
    )


def test_basis_results_are_bounded():
    results = compute_medical_cpi_basis_results(sample_inputs())
    assert 0.0 <= results.fair_yes_probability <= 1.0
    assert results.liquidity_grade in {"A", "B", "C", "D"}
    assert results.signal_label in {"BUY YES", "SELL / AVOID YES", "WATCH"}


def test_path_simulation_shape():
    inputs = sample_inputs()
    df = simulate_basis_paths(inputs, n_paths=500, horizon_months=6)
    assert df.shape == (7, 501)
    assert "month" in df.columns


def test_summary_and_template():
    inputs = sample_inputs()
    results = compute_medical_cpi_basis_results(inputs)
    paths = simulate_basis_paths(inputs, n_paths=500, horizon_months=6)
    summary = summarize_path_distribution(paths, inputs.threshold_bps)
    template = create_scaletrader_basis_template(inputs, results)

    assert {"month", "p10_bps", "p50_bps", "p90_bps", "prob_above_threshold"}.issubset(summary.columns)
    assert "Contract" in template
    assert "Disable conditions" in template
