<div align="center">

# ⚡ BEE 5201: Fleet Simulation & Techno-Economic Analysis

**E-Bike TCO Digital Twin — Comparing Battery Chemistry Ownership vs. Battery-as-a-Service**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

</div>

---

## 📋 Table of Contents

- [Project Objectives](#project-objectives)
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Data Requirements](#data-requirements)
- [Usage](#usage)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Feasibility Report](#feasibility-report)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Project Objectives

1. **Develop a Digital Twin for E-Bike Fleet Operations** — Build a Monte Carlo simulation engine that models 100 electric motorcycles operating on a real Nairobi route, incorporating physics-based energy consumption and electrochemical battery degradation.

2. **Compare SIB vs LFP Battery Chemistry Techno-Economics** — Evaluate Sodium-Ion (SIB) and Lithium Iron Phosphate (LFP) batteries across cost, degradation, energy efficiency, and capacity fade to determine which chemistry is more viable for commercial e-bike fleets.

3. **Assess Owned (Depot) vs BaaS (Swapping) Business Models** — Quantify the Total Cost of Ownership per kilometre for battery ownership with KPLC grid charging versus Battery-as-a-Service with pay-per-swap, identifying crossover points.

4. **Deliver an Interactive Decision-Support Tool** — Create a Streamlit application with separated ETL and simulation stages, configurable parameters, downloadable data, and an automated feasibility report with mathematical derivations.

---

## Overview

A **Monte Carlo fleet simulation** tool that models **100 electric motorcycle (e-bike) riders** (25 per model × 4 models) over a configurable feasibility window (40 / 80 / 120 days) in Nairobi, Kenya. The tool enables fleet operators to compare the **Total Cost of Ownership (TCO)** across four business models spanning two battery chemistries:

| Model | Chemistry | Ownership | Bikes | OPEX Driver |
|-------|-----------|-----------|-------|-------------|
| **SIB Owned** | Sodium-Ion Battery | Fleet purchases battery | 25 | KPLC grid tariff (KSh/kWh) |
| **LFP Owned** | Lithium Iron Phosphate | Fleet purchases battery | 25 | KPLC grid tariff (KSh/kWh) |
| **SIB BaaS** | Sodium-Ion Battery | Operator-owned (swap) | 25 | Per-swap fee (KSh) |
| **LFP BaaS** | Lithium Iron Phosphate | Operator-owned (swap) | 25 | Per-swap fee (KSh) |

### Key Engineering Models

- **Pre-computed Algebraic Energy Decomposition** — Route energy is decomposed into `E(r_dyn) = A + B·r_dyn + C`, enabling ~1000x faster simulation by replacing per-trip array operations with scalar arithmetic.
- **Power-Law SOH Degradation** — `SOH_loss = k × EFC^p` where `k` is extracted from BMS data and `p` = 0.55 (SIB) / 0.50 (LFP).
- **Arrhenius Thermal Stress** — Battery degradation rate scales with ambient temperature: `k_thermal = k_base × 2^((T - 25) / 10)`.
- **Subspace System Identification (SSI)** — Dynamic internal resistance increases as SOH degrades: `r_dyn = R₀ × (1 + 2.5 × (1 - SOH))`.
- **CAPEX Amortization (Capped)** — `CAPEX_amortized = min(CAPEX_initial, CAPEX_initial × (1 - SOH) / 0.20)` — capped at the battery's purchase price (100% consumed at 80% SOH End-of-Life).
- **Stochastic Range Anxiety** — BaaS riders swap batteries at randomised SOC thresholds `θ ~ Uniform(min%, max%)`, simulating real-world behavioural uncertainty across the 25-bike fleet.

---

## Features

- 🔬 **Physics-based simulation** grounded in real BMS cycling data and GPX topography
- 📊 **Interactive Streamlit dashboard** with configurable financial and physical parameters
- ⚡ **Pre-computed energy coefficients** for near-instant simulation runs
- 🌡️ **Arrhenius thermal modelling** for temperature-dependent degradation
- 📈 **5 interactive Plotly charts**: Route topography, SOH fade, energy efficiency, capacity fade, cumulative TCO
- 📥 **Two-phase workflow**: ETL extraction → Simulation (cached, re-runnable with different parameters)
- 📥 **Downloadable ETL data**: Cleaned driving cycles, BMS data, and route profile as CSV
- 🎛️ **Adjustable simulation duration**: 40, 80, or 120 days for progressive observability
- 📋 **Automated feasibility report** with head-to-head comparison table, 5 recommendation sections, and mathematical derivation expanders
- 💰 **Fleet total spend** calculations with per-bike averages and grand total across all 100 bikes
- 📊 **Variance methodology** explaining Bike 0 vs fleet average differences (IEEE 754 precision, stochastic anxiety)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    app.py (UI Layer)                 │
│  Sidebar controls, charts, metrics, download        │
│  buttons, feasibility report, math derivations      │
├─────────────────────────────────────────────────────┤
│                 workflow.py (Logic Engine)           │
│  ┌──────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │ ETL &    │ │ GPX Parser & │ │ FleetBike Digital │ │
│  │ Scaling  │ │ Kinematics   │ │ Twin Class        │ │
│  └──────────┘ └──────────────┘ └──────────────────┘ │
│  ┌──────────────────┐ ┌───────────────────────────┐ │
│  │ Arrhenius Thermal │ │ Pre-computed Energy       │ │
│  │ Stress Model      │ │ Coefficients (A, B, C)    │ │
│  └──────────────────┘ └───────────────────────────┘ │
├─────────────────────────────────────────────────────┤
│                   Input Data Layer                   │
│  Driving Cycles (CSV/Excel) | BMS Data | GPX Route  │
└─────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- pip package manager

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/techno-economic-analysis.git
   cd techno-economic-analysis
   ```

2. **Install dependencies**

   ```bash
   pip install streamlit pandas numpy plotly openpyxl
   ```

3. **Launch the application**

   ```bash
   streamlit run app.py
   ```

4. Open your browser at `http://localhost:8501`

---

## Data Requirements

The application requires three input files:

### 1. Driving Cycles (CSV or Excel)

Daily trip records for e-bike riders.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | int | Unique rider identifier |
| `start_date` | datetime | Trip start date |
| `distance_km` | float | Distance covered per trip (km) |

> **Note:** The ETL filters for user IDs `579236`, `629227`, and `629740`.

### 2. BMS Data (CSV or Excel)

Battery Management System cycling telemetry.

| Column | Type | Description |
|--------|------|-------------|
| `battery_id` | str | Battery identifier (filters for B5, B6, B7) |
| `cycle` | int | Cycle count |
| `SOH` | float | State of Health (%) |
| `chV` / `disV` | float | Charge / Discharge voltage (V) |
| `chI` / `disI` | float | Charge / Discharge current (A) |

### 3. GPX Route File (.gpx or .xml)

Standard GPX 1.1 format with `<trkpt>` elements containing latitude, longitude, and elevation.

```xml
<trkpt lat="-1.2921" lon="36.8219">
  <ele>1670.0</ele>
</trkpt>
```

---

## Usage

### Step 1: Upload & Extract

1. Upload all three data files in the sidebar.
2. Click **📥 Perform ETL** to extract electrochemical parameters.
3. Review the extracted metrics (mean daily distance, degradation coefficient `k`, scaled resistance `R₀`).
4. **Download cleaned data**: Click the download buttons for cleaned driving cycles, BMS data, and route profile CSVs.

### Step 2: Configure & Simulate

1. Adjust financial parameters (KPLC tariff, BaaS swap fee, payload weight).
2. Set range anxiety thresholds and ambient temperature.
3. Choose simulation duration (40 / 80 / 120 days).
4. Click **🚀 Run Simulation**.

### Step 3: Analyse Results

- **Executive verdict**: Identifies the most cost-effective business model (KSh/km).
- **TCO metrics**: Per-km cost for all 4 models.
- **Charts**: SOH degradation, energy efficiency, capacity fade, cumulative cost trends.
- **Feasibility report**: Head-to-head comparison, 5 recommendation sections, fleet total spend, and mathematical derivation expanders.

---

## Configuration

### Sidebar Parameters

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| KPLC Grid Tariff | 10–40 KSh/kWh | 16.0 | Kenya Power grid electricity cost |
| BaaS Swap Fee | 100–300 KSh | 206.0 | Cost per battery swap |
| Payload Weight | 150–300 kg | 200.0 | Bike + rider + cargo mass |
| Min Swap Threshold | 10–30% SOC | 20% | Minimum SOC before range anxiety triggers |
| Max Swap Threshold | 20–50% SOC | 35% | Maximum SOC anxiety threshold |
| Ambient Temperature | 15–27°C | 25°C | Arrhenius thermal stress input |
| Simulation Days | 40, 80, 120 | 40 | Duration of the feasibility window |

### Fixed Constants (in `workflow.py`)

| Constant | Value | Description |
|----------|-------|-------------|
| `TARGET_CAP_KWH` | 1.44 kWh | Target battery capacity (48V × 30Ah) |
| `FLEET_SIZE` | 25 | Number of e-bikes per business model (25 × 4 = 100 total) |

### Theme Configuration (`.streamlit/config.toml`)

```toml
[theme]
base = "dark"
primaryColor = "#FF4B4B"
backgroundColor = "#ffffffff"
secondaryBackgroundColor = "#262730"
textColor = "#020202ff"
```

---

## API Reference

### `workflow.py` — Core Functions

#### `perform_etl_and_scaling(dc_data, bms_data)`

Extracts electrochemical parameters from raw datasets.

- **Parameters:** Streamlit `UploadedFile` objects for driving cycles and BMS data.
- **Returns:** `(mean_km, std_km, k_degradation, r0_scaled, df_daily_clean, df_bms_clean)`
- The two DataFrames are cleaned intermediate data available for download.

#### `apply_arrhenius_thermal_stress(k_base, current_temp, baseline_temp=25.0)`

Adjusts degradation coefficient `k` for ambient temperature.

- **Formula:** `k_adjusted = k_base × 2^((T - 25) / 10)`
- **Returns:** Thermally adjusted `k` value.

#### `parse_real_gpx(gpx_data)`

Parses GPX files into distance/gradient/velocity profiles.

- **Returns:** `(DataFrame, route_km)` — DataFrame with columns `lat`, `lon`, `ele`, `dist_m`, `grad`, `v_ms`.

#### `precompute_route_energy_coefficients(df_route, eff_base_wh_km, payload)`

Decomposes route energy into three scalar coefficients.

- **Returns:** `(A, B, C)` where `Energy(r_dyn) = A + B × r_dyn + C` (in Joules).

#### `fast_trip_energy(A, B, C, r_dyn)`

Computes trip energy from pre-computed coefficients in a single scalar operation.

- **Returns:** Energy in Wh.

#### `run_fleet_simulation(...)`

Main simulation entry point. Runs all 4 fleet models (25 bikes each) over the specified duration.

- **Key Parameters:** `env_temp` (°C), `sim_days` (40/80/120), `progress_callback` (callable).
- **Returns:** `(fleets_dict, results_dict, best_model_name)`

### `FleetBike` — Digital Twin Class

Each instance tracks: `soh`, `soc`, `cum_efc`, `total_km`, `opex`, `capex_amortized`, and daily telemetry logs for charting. Key attributes:

| Attribute | Description |
|-----------|-------------|
| `energy_A`, `energy_B`, `energy_C` | Pre-computed route energy coefficients |
| `r0_base` | Baseline internal resistance (Ω) |
| `k_coeff` | Thermally-adjusted degradation coefficient |
| `p_factor` | Power-law exponent (SIB: 0.55, LFP: 0.50) |
| `initial_capex` | Battery purchase price (KSh) |
| `log_soh`, `log_wh_km`, `log_cap`, `log_cum_tco` | Daily telemetry arrays |

---

## Feasibility Report

After simulation, the app generates an automated **📋 Feasibility Report** containing:

### ⚖️ Head-to-Head Comparison Table

SIB vs LFP across 6 metrics (TCO owned, TCO BaaS, SOH, SOH loss, Wh/km, remaining Ah) with a ✅ winner column.

### 📝 Recommendations (5 sections)

1. **Cost Efficiency (TCO/km)** — Winner per business model with savings per km.
2. **Battery Longevity (SOH Degradation)** — Includes expandable derivation:
   - 8 calculation steps from route physics → P_mech → coefficients (A, B, C) → E_trip → EFC → Arrhenius k → power-law SOH
3. **Energy Efficiency (Wh/km)** — Includes expandable derivation:
   - Dynamic resistance → E_trip at end → Wh/km with Day 0 vs Day N comparison
4. **Capacity Fade (Ah)** — Includes expandable derivation:
   - C_remaining = 30 Ah × SOH with worked examples
5. **Cumulative TCO Accumulation** — Fleet-average per-bike costs + fleet total spend table:
   - Per-bike averages (fleet total ÷ 25) with daily burn rates
   - Total fleet spend table (all 25 bikes per model + grand total for 100 bikes)
   - Crossover point detection (where Owned overtakes BaaS)
   - Expandable mathematical derivation (OPEX, CAPEX, worked examples)
   - Expandable variance methodology (IEEE 754 precision, stochastic anxiety, min/max spread)

### 🏆 Overall Verdict

Best chemistry for Owned, best for BaaS, and overall most cost-effective path.

---

## Project Structure

```
TECHNO ECONOMIC ANALYSIS/
├── app.py                  # Streamlit UI layer (dashboard, charts, feasibility report)
├── workflow.py             # Core simulation engine (ETL, physics, digital twin)
├── README.md               # This file
└── .streamlit/
    └── config.toml         # Theme configuration
```

---

## Contributing

### Getting Started

1. Fork this repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and test locally with `streamlit run app.py`.
4. Commit with descriptive messages: `git commit -m "Add: description of change"`
5. Push and open a Pull Request.

### Code Style

- Follow PEP 8 conventions.
- Add docstrings to all public functions.
- Keep UI code in `app.py` and logic in `workflow.py`.
- Use NumPy vectorisation over Python loops where possible.

### Areas for Contribution

- Additional battery chemistries (NMC, LTO).
- Multi-route simulation with route selection dropdown.
- Export simulation results to PDF/Excel reports.
- Database integration for historical run comparison.
- Unit tests for physics calculations.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'openpyxl'`

Excel file support requires openpyxl:

```bash
pip install openpyxl
```

### `streamlit: command not found`

Use the Python module syntax:

```bash
python -m streamlit run app.py
```

### Files upload but nothing happens

- Ensure **all three files** (Driving Cycles, BMS Data, GPX) are uploaded before clicking **Perform ETL**.
- Check that your CSV/Excel files contain the expected column names (`user_id`, `start_date`, `distance_km`, `battery_id`, `cycle`, `SOH`, etc.).

### Simulation runs slowly

- Start with **40 days** instead of 120 for quick trend observation.
- The pre-computed energy coefficients should make 25-bike simulations run in under a second.

### GPX parsing errors

- Ensure the GPX file uses the standard namespace: `http://www.topografix.com/GPX/1/1`.
- Each `<trkpt>` must include `lat` and `lon` attributes. The `<ele>` tag is optional (defaults to 0.0).

### Charts show flat lines or no data

- Verify your BMS data contains records for battery IDs `B5`, `B6`, `B7` with `cycle > 0`.
- Verify your driving cycle data contains records for user IDs `579236`, `629227`, `629740`.

### CAPEX Amortized exceeds initial cost

- This was fixed: CAPEX amortization is now **capped at the initial battery price**. If you see values exceeding initial CAPEX, update to the latest `workflow.py`.

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 BEE 5201 Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Built for BEE 5201** | E-Mobility Techno-Economic Analysis

</div>
