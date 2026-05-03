# Medical CPI vs. CPI Basis Mode 2 — Integrated Patch

## What changed

This patch fully integrates a second simulation mode into the existing Streamlit app.

The app now has a top-level mode selector:

```text
Simulation Mode:
[ General CPI RV ] [ Medical CPI vs CPI Basis ]
```

## Files changed / added

```text
app.py                                      # updated top-level router and app copy
medical_cpi_basis_sim_tab.py                # new integrated Mode 2 UI + simulation module
tests/test_medical_cpi_basis_sim.py         # smoke tests for Mode 2 pure functions
docs/handoffs/MEDICAL_CPI_BASIS_MODE2_INTEGRATION.md
```

## Mode 2 purpose

Mode 2 demonstrates how Oriel can turn a healthcare-inflation basis dislocation into an execution-intelligence workflow.

Illustrative contract:

```text
Medical CPI YoY − CPI-U YoY > threshold
```

The UI includes:

- headline CPI-U YoY assumption;
- hospital services, physician services, prescription drugs, and other medical YoY assumptions;
- adjustable medical CPI proxy weights;
- basis threshold and market YES price;
- confidence / liquidity scores;
- clip size, max position, and starting inventory;
- fair YES probability;
- edge vs market price;
- simulated basis distribution;
- probability of finishing above threshold;
- PnL / EV diagnostics;
- ScaleTrader-style basis ticket.

## Dependencies

No new package dependencies were added. The module uses packages already in `requirements.txt`:

```text
streamlit
plotly
pandas
numpy
```

## Test instructions

From repo root:

```bash
python -m pytest tests/test_medical_cpi_basis_sim.py
```

Or, without pytest:

```bash
python - <<'PY'
from medical_cpi_basis_sim_tab import MedicalCpiBasisInputs, compute_medical_cpi_basis_results
x = MedicalCpiBasisInputs(0.032,0.058,0.047,0.039,0.042,0.30,0.20,0.15,0.35,100,0.42,175,0.82,0.74,2000,250,0)
print(compute_medical_cpi_basis_results(x))
PY
```

## Deployment reminder

Deploy as the existing review app:

```text
Repo: Oriel-CareFi/oriel-market-sim-forecasttrader-review
URL:  https://oriel-market-sim-forecasttrader.streamlit.app
Access: public Streamlit app + password gate
```

Streamlit Secrets should still include:

```toml
review_password = "choose-a-strong-review-password"
REVIEW_BUILD = "true"
```

## Acceptance criteria

- Existing General CPI RV simulation still renders.
- New Medical CPI vs CPI Basis mode renders from the top-level selector.
- Mode 2 charts and ticket template render without errors.
- Password gate remains active in review deployment.
- No secrets are committed.
