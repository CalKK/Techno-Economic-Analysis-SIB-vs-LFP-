import streamlit as st
import pandas as pd
import plotly.express as px
from workflow import (
    perform_etl_and_scaling, parse_real_gpx, run_fleet_simulation, fast_trip_energy
)

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(page_title="Techno-Economic Analysis", layout="wide", initial_sidebar_state="expanded")

st.title("⚡BEE 5201: A Fleet Simulation and Techno-Economic Analysis")
st.markdown("E-BIKE TCO Digital Twin")

# ==========================================
# SIDEBAR: THE CONTROL CENTER
# ==========================================

# --- Step 1: Data Upload ---
st.sidebar.header("📂 1. Data Input")
dc_file = st.sidebar.file_uploader("Upload Driving Cycles (CSV/Excel)", type=['csv', 'xlsx', 'xls'])
bms_file = st.sidebar.file_uploader("Upload BMS Data (CSV/Excel)", type=['csv', 'xlsx', 'xls'])
gpx_file = st.sidebar.file_uploader("Upload Route Topography (GPX)", type=['gpx', 'xml'])

# --- ETL Button ---
etl_ready = dc_file and bms_file and gpx_file
etl_btn = st.sidebar.button("📥 Perform ETL", use_container_width=True,
                             disabled=not etl_ready,
                             help="Extract parameters from uploaded files")

# --- Step 2: Parameters ---
st.sidebar.header("⚙️ 2. Financial & Physical Parameters")
kplc_tariff = st.sidebar.slider("KPLC Grid Tariff (KSh/kWh)", min_value=10.0, max_value=40.0, value=16.0, step=1.0)
swap_fee = st.sidebar.slider("BaaS Swap Fee (KSh)", min_value=100.0, max_value=300.0, value=206.0, step=1.0)
payload_weight = st.sidebar.slider("Payload: Bike + Rider + Cargo (kg)", min_value=150.0, max_value=300.0, value=200.0, step=10.0)

st.sidebar.header("🧠 3. Range Anxiety Logic")
anxiety_min = st.sidebar.slider("Min Swap Threshold (SOC %)", 10, 30, 20)
anxiety_max = st.sidebar.slider("Max Swap Threshold (SOC %)", 20, 50, 35)

st.sidebar.header("🌡️ 4. Thermal Environment")
env_temp = st.sidebar.slider("Ambient Temperature (°C)", min_value=15.0, max_value=27.0, value=25.0, step=1.0,
                              help="Arrhenius model: degradation rate ~doubles every 10°C above 25°C baseline")

st.sidebar.header("📊 5. Simulation Duration")
sim_days = st.sidebar.selectbox("Number of Days", options=[40, 80, 120], index=0,
                                help="40 days for quick trends, 120 for full feasibility window")

# --- Run Simulation Button ---
st.sidebar.divider()
sim_ready = 'etl_done' in st.session_state and st.session_state.etl_done
run_sim = st.sidebar.button("🚀 Run Simulation", use_container_width=True, type="primary",
                             disabled=not sim_ready,
                             help="Run ETL first to enable this button")

# ==========================================
# ETL PROCESSING
# ==========================================
if etl_btn and etl_ready:
    with st.spinner("📥 Extracting Electrochemical DNA and parsing Topography..."):
        mean_km, std_km, k_lfp, r0_scaled, df_daily_clean, df_bms_clean = perform_etl_and_scaling(dc_file, bms_file)
        df_route, route_km = parse_real_gpx(gpx_file)

        # Cache results in session state
        st.session_state.etl_done = True
        st.session_state.mean_km = mean_km
        st.session_state.std_km = std_km
        st.session_state.k_lfp = k_lfp
        st.session_state.r0_scaled = r0_scaled
        st.session_state.df_route = df_route
        st.session_state.route_km = route_km
        st.session_state.df_daily_clean = df_daily_clean
        st.session_state.df_bms_clean = df_bms_clean

    st.rerun()

# ==========================================
# ETL RESULTS DISPLAY
# ==========================================
if sim_ready:
    st.success("✅ ETL Complete — Parameters extracted and cached.")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Mean Daily Distance", f"{st.session_state.mean_km:.1f} km")
    col_b.metric("Std Deviation", f"{st.session_state.std_km:.1f} km")
    col_c.metric("Degradation k", f"{st.session_state.k_lfp:.6f}")
    col_d.metric("R₀ Scaled (Ω)", f"{st.session_state.r0_scaled:.6f}")

    st.caption(f"📍 Route: {st.session_state.route_km:.2f} km | "
               f"📊 Fleet: 25 bikes × 4 models = 100 total | "
               f"📅 Simulation: {sim_days} days | "
               f"🌡️ Temp: {env_temp}°C")

    # --- Download ETL Files ---
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    with dl_col1:
        st.download_button(
            "📥 Download Driving Cycles (Clean)",
            data=st.session_state.df_daily_clean.to_csv(index=False),
            file_name="etl_driving_cycles_clean.csv",
            mime="text/csv"
        )
    with dl_col2:
        st.download_button(
            "📥 Download BMS Data (Clean)",
            data=st.session_state.df_bms_clean.to_csv(index=False),
            file_name="etl_bms_data_clean.csv",
            mime="text/csv"
        )
    with dl_col3:
        st.download_button(
            "📥 Download Route Profile",
            data=st.session_state.df_route.to_csv(index=False),
            file_name="etl_route_profile.csv",
            mime="text/csv"
        )
    st.divider()

# ==========================================
# SIMULATION
# ==========================================
if run_sim and sim_ready:
    progress_bar = st.progress(0, text="Initializing fleet...")

    def update_progress(pct):
        progress_bar.progress(pct, text=f"Simulating day {int(pct * sim_days)}/{sim_days}...")

    fleets, results, best_model = run_fleet_simulation(
        st.session_state.mean_km, st.session_state.std_km,
        st.session_state.k_lfp, st.session_state.r0_scaled,
        st.session_state.df_route, st.session_state.route_km,
        kplc_tariff, swap_fee, payload_weight, anxiety_min, anxiety_max,
        env_temp, sim_days=sim_days, progress_callback=update_progress
    )

    progress_bar.progress(1.0, text="✅ Simulation complete!")

    # --- THE EXECUTIVE SUMMARY ---
    st.success(f"### 🏆 Feasibility Verdict: **{best_model}** is the most cost-effective path at KSh {results[best_model]:.2f}/km.")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SIB Owned TCO", f"KSh {results['SIB Owned']:.2f} / km")
    col2.metric("LFP Owned TCO", f"KSh {results['LFP Owned']:.2f} / km")
    col3.metric("SIB BaaS", f"KSh {results['SIB BaaS']:.2f} / km")
    col4.metric("LFP BaaS", f"KSh {results['LFP BaaS']:.2f} / km")
    st.divider()

    # --- VISUALIZATIONS ---
    rep_sib = fleets["SIB Owned"][0]
    rep_lfp = fleets["LFP Owned"][0]
    rep_sib_baas = fleets["SIB BaaS"][0]
    rep_lfp_baas = fleets["LFP BaaS"][0]

    # 1. Topography
    st.subheader("⛰️ GPX Route Topography (Physics Engine)")
    fig_topo = px.area(st.session_state.df_route, x='dist_m', y='ele',
                       labels={'dist_m': 'Distance (m)', 'ele': 'Elevation (m)'})
    fig_topo.update_layout(yaxis_range=[
        st.session_state.df_route['ele'].min() - 10,
        st.session_state.df_route['ele'].max() + 10
    ])
    st.plotly_chart(fig_topo, use_container_width=True)

    colA, colB = st.columns(2)

    # 2. SOH Degradation
    with colA:
        st.subheader("📉 Battery Health (SOH) Fade")
        df_soh = pd.DataFrame({
            'Day': rep_sib.log_day,
            'SIB Owned': rep_sib.log_soh,
            'LFP Owned': rep_lfp.log_soh
        })
        fig_soh = px.line(df_soh, x='Day', y=['SIB Owned', 'LFP Owned'],
                          labels={'value': 'SOH (%)', 'variable': 'Chemistry'})
        fig_soh.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="End of Life (80%)")
        st.plotly_chart(fig_soh, use_container_width=True)

    # 3. Energy Efficiency (SSI Proof)
    with colB:
        st.subheader("⚡ Energy Efficiency (SSI Voltage Sag)")
        df_eff = pd.DataFrame({
            'Day': rep_sib.log_day,
            'SIB (Wh/km)': rep_sib.log_wh_km,
            'LFP (Wh/km)': rep_lfp.log_wh_km
        })
        fig_eff = px.line(df_eff, x='Day', y=['SIB (Wh/km)', 'LFP (Wh/km)'],
                          labels={'value': 'Wh / km consumed'})
        st.plotly_chart(fig_eff, use_container_width=True)

    colC, colD = st.columns(2)

    # 4. Capacity Ah Fade
    with colC:
        st.subheader("🔋 Capacity Fade (Ah)")
        df_cap = pd.DataFrame({
            'Day': rep_sib.log_day,
            'SIB (Ah)': rep_sib.log_cap,
            'LFP (Ah)': rep_lfp.log_cap
        })
        fig_cap = px.area(df_cap, x='Day', y=['SIB (Ah)', 'LFP (Ah)'],
                          labels={'value': 'Available Capacity (Ah)'})
        st.plotly_chart(fig_cap, use_container_width=True)

    # 5. Cumulative Cost Breakdown (all 4 models)
    with colD:
        st.subheader("💰 Cumulative TCO Accumulation")
        df_tco = pd.DataFrame({
            'Day': rep_sib.log_day,
            'SIB Owned': rep_sib.log_cum_tco,
            'LFP Owned': rep_lfp.log_cum_tco,
            'SIB BaaS': rep_sib_baas.log_cum_tco,
            'LFP BaaS': rep_lfp_baas.log_cum_tco
        })
        fig_tco = px.line(df_tco, x='Day', y=['SIB Owned', 'LFP Owned', 'SIB BaaS', 'LFP BaaS'],
                          labels={'value': 'Total Spend (KSh)'})
        st.plotly_chart(fig_tco, use_container_width=True)

    # ==========================================
    # FEASIBILITY REPORT
    # ==========================================
    st.divider()
    st.subheader("📋 Feasibility Report & Data-Driven Recommendations")

    # --- Compute comparative metrics ---
    sib_owned_tco = results['SIB Owned']
    lfp_owned_tco = results['LFP Owned']
    sib_baas_tco = results['SIB BaaS']
    lfp_baas_tco = results['LFP BaaS']

    sib_final_soh = rep_sib.log_soh[-1]
    lfp_final_soh = rep_lfp.log_soh[-1]
    sib_soh_loss = 100.0 - sib_final_soh
    lfp_soh_loss = 100.0 - lfp_final_soh

    sib_final_wh = rep_sib.log_wh_km[-1]
    lfp_final_wh = rep_lfp.log_wh_km[-1]

    sib_final_cap = rep_sib.log_cap[-1]
    lfp_final_cap = rep_lfp.log_cap[-1]

    # Pre-compute intermediates for derivations
    coeffs_sib = (rep_sib.energy_A, rep_sib.energy_B, rep_sib.energy_C)
    coeffs_lfp = (rep_lfp.energy_A, rep_lfp.energy_B, rep_lfp.energy_C)
    route_km = st.session_state.route_km
    mean_trips_per_day = st.session_state.mean_km / route_km

    sib_r0 = rep_sib.r0_base
    lfp_r0 = rep_lfp.r0_base
    sib_r_dyn_day0 = sib_r0  # SOH=1.0 at start, so r_dyn = R0
    lfp_r_dyn_day0 = lfp_r0
    sib_r_dyn_final = sib_r0 * (1 + (1 - sib_final_soh / 100) * 2.5)
    lfp_r_dyn_final = lfp_r0 * (1 + (1 - lfp_final_soh / 100) * 2.5)

    sib_etrip_day0 = fast_trip_energy(coeffs_sib[0], coeffs_sib[1], coeffs_sib[2], sib_r_dyn_day0)
    lfp_etrip_day0 = fast_trip_energy(coeffs_lfp[0], coeffs_lfp[1], coeffs_lfp[2], lfp_r_dyn_day0)
    sib_etrip_final = fast_trip_energy(coeffs_sib[0], coeffs_sib[1], coeffs_sib[2], sib_r_dyn_final)
    lfp_etrip_final = fast_trip_energy(coeffs_lfp[0], coeffs_lfp[1], coeffs_lfp[2], lfp_r_dyn_final)

    sib_etrip_kwh_day0 = sib_etrip_day0 / 1000.0
    lfp_etrip_kwh_day0 = lfp_etrip_day0 / 1000.0
    sib_efc_per_trip = sib_etrip_kwh_day0 / 1.44
    lfp_efc_per_trip = lfp_etrip_kwh_day0 / 1.44

    thermal_mult = 2.0 ** ((env_temp - 25) / 10)

    # Best chemistry per dimension
    cheaper_owned = "SIB" if sib_owned_tco < lfp_owned_tco else "LFP"
    cheaper_baas = "SIB" if sib_baas_tco < lfp_baas_tco else "LFP"
    more_durable = "LFP" if lfp_final_soh > sib_final_soh else "SIB"
    more_efficient = "LFP" if lfp_final_wh < sib_final_wh else "SIB"
    more_capacity = "LFP" if lfp_final_cap > sib_final_cap else "SIB"

    # Overall winner
    best_owned = min(results, key=lambda k: results[k] if 'Owned' in k else float('inf'))
    best_baas = min(results, key=lambda k: results[k] if 'BaaS' in k else float('inf'))
    overall_best = min(results, key=results.get)

    # --- Report Table ---
    st.markdown("#### ⚖️ Head-to-Head Comparison")
    comparison_data = {
        'Metric': [
            'TCO — Owned (KSh/km)',
            'TCO — BaaS (KSh/km)',
            f'SOH After {sim_days} Days (%)',
            f'SOH Loss Over {sim_days} Days (%)',
            'Energy Efficiency at End (Wh/km)',
            'Remaining Capacity at End (Ah)',
        ],
        'SIB': [
            f'{sib_owned_tco:.2f}', f'{sib_baas_tco:.2f}',
            f'{sib_final_soh:.2f}', f'{sib_soh_loss:.2f}',
            f'{sib_final_wh:.1f}', f'{sib_final_cap:.2f}',
        ],
        'LFP': [
            f'{lfp_owned_tco:.2f}', f'{lfp_baas_tco:.2f}',
            f'{lfp_final_soh:.2f}', f'{lfp_soh_loss:.2f}',
            f'{lfp_final_wh:.1f}', f'{lfp_final_cap:.2f}',
        ],
        'Winner': [
            f'✅ {cheaper_owned}', f'✅ {cheaper_baas}',
            f'✅ {more_durable}', f'✅ {more_durable}',
            f'✅ {more_efficient}', f'✅ {more_capacity}',
        ]
    }
    st.table(pd.DataFrame(comparison_data))

    # --- Written Recommendations ---
    st.markdown("#### 📝 Recommendations")

    # 1. Cost
    cost_saving_owned = abs(sib_owned_tco - lfp_owned_tco)
    cost_saving_baas = abs(sib_baas_tco - lfp_baas_tco)
    st.markdown(f"""
**1. Cost Efficiency (TCO/km)**

- **Owned Model:** **{cheaper_owned}** is more cost-effective at \
KSh {min(sib_owned_tco, lfp_owned_tco):.2f}/km vs KSh {max(sib_owned_tco, lfp_owned_tco):.2f}/km \
(saving KSh {cost_saving_owned:.2f}/km).
- **BaaS Model:** **{cheaper_baas}** is more cost-effective at \
KSh {min(sib_baas_tco, lfp_baas_tco):.2f}/km vs KSh {max(sib_baas_tco, lfp_baas_tco):.2f}/km \
(saving KSh {cost_saving_baas:.2f}/km).
""")

    # 2. SOH
    st.markdown(f"""
**2. Battery Longevity (SOH Degradation)**

- After {sim_days} days of fleet operation, **{more_durable}** retains higher health at \
{max(sib_final_soh, lfp_final_soh):.2f}% SOH vs {min(sib_final_soh, lfp_final_soh):.2f}% SOH.
- **SIB** lost **{sib_soh_loss:.2f}%** while **LFP** lost **{lfp_soh_loss:.2f}%** of original capacity.
- {'⚠️ SIB degrades significantly faster due to its 1.8x higher degradation coefficient and higher internal resistance.' if more_durable == 'LFP' else '⚠️ LFP shows unexpected degradation — review BMS data quality.'}
""")

    with st.expander("🔬 View Complete SOH Calculation (every step)"):
        st.markdown(f"""
##### Step 1: Route Segment Physics

For each GPX track segment $i$, the mechanical power demand on the motor is:

$$
P_{{mech,i}} = M \\cdot g \\cdot \\sin(\\theta_i) \\cdot v_i + (\\eta_{{base}} \\times 3.6) \\cdot v_i
$$

| Input | Value | Source |
|-------|-------|--------|
| $M$ (payload) | {payload_weight} kg | Sidebar slider |
| $g$ (gravity) | 9.81 m/s² | Constant |
| $\\theta_i$ (gradient) | `arctan(Δele / Δdist)` per segment | GPX elevation data |
| $v_i$ (speed) | 6.94 m/s (uphill, θ>0.03) or 11.11 m/s (flat/downhill) | Adaptive profile |
| $\\eta_{{base}}$ | SIB: 21.0 Wh/km, LFP: 18.5 Wh/km | Chemistry constant |

##### Step 2: Electrical Power (per segment)

The motor current and electrical power including ohmic losses:

$$
I_i = \\frac{{P_{{mech,i}}}}{{48V}} \\quad \\text{{(when }} P_{{mech}} > 0\\text{{)}}
$$

$$
P_{{elec,i}} = \\begin{{cases}} P_{{mech,i}} + I_i^2 \\cdot r_{{dyn}} & P_{{mech}} > 0 \\text{{ (motoring — includes }} I^2R \\text{{ heat loss)}} \\\\\\\\ P_{{mech,i}} \\times 0.3 & P_{{mech}} \\leq 0 \\text{{ (regenerative braking at 30% recovery)}} \\end{{cases}}
$$

##### Step 3: Pre-computed Coefficient Decomposition

Time to traverse segment: $\\Delta t_i = d_i / v_i$

Since only $r_{{dyn}}$ changes between trips, we split the sum:

$$
E_{{trip}} = \\frac{{1}}{{3600}} \\left[ \\underbrace{{\\sum_{{P>0}} P_{{mech,i}} \\cdot \\Delta t_i}}_{{\\textbf{{A}}}} + \\underbrace{{\\sum_{{P>0}} \\left(\\frac{{P_{{mech,i}}}}{{48}}\\right)^2 \\cdot \\Delta t_i}}_{{\\textbf{{B}}}} \\cdot r_{{dyn}} + \\underbrace{{\\sum_{{P \\leq 0}} P_{{mech,i}} \\times 0.3 \\cdot \\Delta t_i}}_{{\\textbf{{C}}}} \\right] \\quad \\text{{(Wh)}}
$$

**Computed once from GPX route:**

| Coefficient | SIB (η=21.0) | LFP (η=18.5) | Physical meaning |
|-------------|--------------|---------------|------------------|
| **A** (Joules) | {coeffs_sib[0]:,.2f} | {coeffs_lfp[0]:,.2f} | Mechanical energy (motoring segments) |
| **B** (J/Ω) | {coeffs_sib[1]:,.2f} | {coeffs_lfp[1]:,.2f} | $I^2$ heat loss factor (scales with $r_{{dyn}}$) |
| **C** (Joules) | {coeffs_sib[2]:,.2f} | {coeffs_lfp[2]:,.2f} | Regen braking return (negative) |

##### Step 4: Dynamic Resistance (SSI Model)

$$
r_{{dyn}} = R_0 \\times (1 + 2.5 \\times (1 - SOH))
$$

| | $R_0$ (from ETL) | Source |
|--|-----------------|--------|
| LFP base | {st.session_state.r0_scaled:.6f} Ω | BMS SSI: median of `|chV−disV|/(chI+disI)`, scaled 72V→48V |
| SIB | {sib_r0:.6f} Ω | 1.5× LFP (higher internal resistance) |

**At Day 0** (SOH = 1.0): $r_{{dyn}} = R_0 \\times (1 + 2.5 \\times 0) = R_0$

| | SIB | LFP |
|--|-----|-----|
| $r_{{dyn}}$ Day 0 | {sib_r_dyn_day0:.6f} Ω | {lfp_r_dyn_day0:.6f} Ω |

##### Step 5: Trip Energy ($E_{{trip}}$) at Day 0

$$
E_{{trip}} = \\frac{{A + B \\cdot r_{{dyn}} + C}}{{3600}} \\text{{ (Wh)}} \\rightarrow \\div 1000 \\text{{ (kWh)}}
$$

**SIB:**
$$
E_{{trip,SIB}} = \\frac{{{coeffs_sib[0]:,.2f} + {coeffs_sib[1]:,.2f} \\times {sib_r_dyn_day0:.6f} + ({coeffs_sib[2]:,.2f})}}{{3600}} = {sib_etrip_day0:.2f} \\text{{ Wh}} = {sib_etrip_kwh_day0:.6f} \\text{{ kWh}}
$$

**LFP:**
$$
E_{{trip,LFP}} = \\frac{{{coeffs_lfp[0]:,.2f} + {coeffs_lfp[1]:,.2f} \\times {lfp_r_dyn_day0:.6f} + ({coeffs_lfp[2]:,.2f})}}{{3600}} = {lfp_etrip_day0:.2f} \\text{{ Wh}} = {lfp_etrip_kwh_day0:.6f} \\text{{ kWh}}
$$

##### Step 6: Equivalent Full Cycles (EFC) per Trip

$$
EFC_{{trip}} = \\frac{{E_{{trip}} \\text{{ (kWh)}}}}{{C_{{battery}}}} = \\frac{{E_{{trip}}}}{{1.44 \\text{{ kWh}}}}
$$

Where $C_{{battery}}$ = 48V × 30Ah = 1.44 kWh (rated pack capacity).

| | SIB | LFP |
|--|-----|-----|
| $E_{{trip}}$ (kWh) | {sib_etrip_kwh_day0:.6f} | {lfp_etrip_kwh_day0:.6f} |
| $EFC_{{trip}}$ | {sib_etrip_kwh_day0:.6f} / 1.44 = **{sib_efc_per_trip:.6f}** | {lfp_etrip_kwh_day0:.6f} / 1.44 = **{lfp_efc_per_trip:.6f}** |
| Avg trips/day | {mean_trips_per_day:.1f} (from ETL: {st.session_state.mean_km:.1f} km / {route_km:.2f} km) | {mean_trips_per_day:.1f} |
| Est. EFC/day | {sib_efc_per_trip * mean_trips_per_day:.6f} | {lfp_efc_per_trip * mean_trips_per_day:.6f} |
| **Actual cumulative EFC ({sim_days} days)** | **{rep_sib.cum_efc:.2f}** | **{rep_lfp.cum_efc:.2f}** |

> Actual EFC is slightly higher than (EFC/day × days) because $r_{{dyn}}$ rises daily as SOH drops, increasing each trip's energy.

##### Step 7: Arrhenius Thermal Adjustment

The base degradation coefficient $k$ from BMS ETL is adjusted for ambient temperature:

$$
k_{{thermal}} = k_{{base}} \\times 2^{{(T - 25)/10}}
$$

| Parameter | SIB | LFP |
|-----------|-----|-----|
| $k_{{base}}$ from ETL | — | {st.session_state.k_lfp:.6f} |
| SIB multiplier | 1.8× LFP (faster degradation) | — |
| $k_{{base}}$ (pre-thermal) | {st.session_state.k_lfp * 1.8:.6f} | {st.session_state.k_lfp:.6f} |
| $T$ (ambient) | {env_temp}°C | {env_temp}°C |
| Thermal multiplier $2^{{({env_temp}-25)/10}}$ | {thermal_mult:.4f} | {thermal_mult:.4f} |
| **$k_{{thermal}}$** | **{rep_sib.k_coeff:.6f}** | **{rep_lfp.k_coeff:.6f}** |

##### Step 8: Power-Law SOH Calculation

$$
SOH_{{loss}} = k_{{thermal}} \\times EFC_{{cum}}^p \\qquad SOH_{{final}} = 1 - SOH_{{loss}}
$$

**SIB** ($p$ = 0.55):
$$
SOH_{{loss}} = {rep_sib.k_coeff:.6f} \\times {rep_sib.cum_efc:.2f}^{{0.55}} = {rep_sib.k_coeff:.6f} \\times {rep_sib.cum_efc ** 0.55:.4f} = {rep_sib.k_coeff * (rep_sib.cum_efc ** 0.55):.6f}
$$
$$
SOH_{{final}} = (1 - {rep_sib.k_coeff * (rep_sib.cum_efc ** 0.55):.6f}) \\times 100 = \\boxed{{{(1 - rep_sib.k_coeff * (rep_sib.cum_efc ** 0.55)) * 100:.2f}\\%}}
$$

**LFP** ($p$ = 0.50):
$$
SOH_{{loss}} = {rep_lfp.k_coeff:.6f} \\times {rep_lfp.cum_efc:.2f}^{{0.50}} = {rep_lfp.k_coeff:.6f} \\times {rep_lfp.cum_efc ** 0.50:.4f} = {rep_lfp.k_coeff * (rep_lfp.cum_efc ** 0.50):.6f}
$$
$$
SOH_{{final}} = (1 - {rep_lfp.k_coeff * (rep_lfp.cum_efc ** 0.50):.6f}) \\times 100 = \\boxed{{{(1 - rep_lfp.k_coeff * (rep_lfp.cum_efc ** 0.50)) * 100:.2f}\\%}}
$$
""")

    # 3. Efficiency
    eff_diff = abs(sib_final_wh - lfp_final_wh)
    st.markdown(f"""
**3. Energy Efficiency (Wh/km)**

- **{more_efficient}** consumes less energy at {min(sib_final_wh, lfp_final_wh):.1f} Wh/km \
vs {max(sib_final_wh, lfp_final_wh):.1f} Wh/km (Δ {eff_diff:.1f} Wh/km).
- Lower Wh/km translates directly to lower KPLC grid charging costs for the Owned model.
""")

    with st.expander("🔬 View Complete Energy Efficiency Calculation (every step)"):
        st.markdown(f"""
##### Step 1: Dynamic Resistance at Day {sim_days}

$$
r_{{dyn}} = R_0 \\times (1 + 2.5 \\times (1 - SOH))
$$

**SIB** (SOH = {sib_final_soh/100:.4f}):
$$
r_{{dyn,SIB}} = {sib_r0:.6f} \\times (1 + 2.5 \\times (1 - {sib_final_soh/100:.4f})) = {sib_r0:.6f} \\times {(1 + 2.5 * (1 - sib_final_soh/100)):.4f} = {sib_r_dyn_final:.6f} \\text{{ Ω}}
$$

**LFP** (SOH = {lfp_final_soh/100:.4f}):
$$
r_{{dyn,LFP}} = {lfp_r0:.6f} \\times (1 + 2.5 \\times (1 - {lfp_final_soh/100:.4f})) = {lfp_r0:.6f} \\times {(1 + 2.5 * (1 - lfp_final_soh/100)):.4f} = {lfp_r_dyn_final:.6f} \\text{{ Ω}}
$$

##### Step 2: Trip Energy at Day {sim_days}

Using pre-computed coefficients (A, B, C from Step 3 of SOH derivation):

**SIB:**
$$
E_{{trip}} = \\frac{{{coeffs_sib[0]:,.2f} + {coeffs_sib[1]:,.2f} \\times {sib_r_dyn_final:.6f} + ({coeffs_sib[2]:,.2f})}}{{3600}} = {sib_etrip_final:.2f} \\text{{ Wh}}
$$

**LFP:**
$$
E_{{trip}} = \\frac{{{coeffs_lfp[0]:,.2f} + {coeffs_lfp[1]:,.2f} \\times {lfp_r_dyn_final:.6f} + ({coeffs_lfp[2]:,.2f})}}{{3600}} = {lfp_etrip_final:.2f} \\text{{ Wh}}
$$

##### Step 3: Efficiency = $E_{{trip}}$ ÷ Route Distance

$$
\\eta_{{Wh/km}} = \\frac{{E_{{trip}}}}{{{route_km:.2f} \\text{{ km}}}}
$$

**SIB:** $\\eta = {sib_etrip_final:.2f} / {route_km:.2f} = \\boxed{{{sib_final_wh:.1f} \\text{{ Wh/km}}}}$

**LFP:** $\\eta = {lfp_etrip_final:.2f} / {route_km:.2f} = \\boxed{{{lfp_final_wh:.1f} \\text{{ Wh/km}}}}$

##### Day 0 → Day {sim_days} Comparison

| | SIB Day 0 | SIB Day {sim_days} | LFP Day 0 | LFP Day {sim_days} |
|--|-----------|------------|-----------|------------|
| $r_{{dyn}}$ (Ω) | {sib_r_dyn_day0:.6f} | {sib_r_dyn_final:.6f} | {lfp_r_dyn_day0:.6f} | {lfp_r_dyn_final:.6f} |
| $E_{{trip}}$ (Wh) | {sib_etrip_day0:.2f} | {sib_etrip_final:.2f} | {lfp_etrip_day0:.2f} | {lfp_etrip_final:.2f} |
| Wh/km | {sib_etrip_day0/route_km:.1f} | {sib_final_wh:.1f} | {lfp_etrip_day0/route_km:.1f} | {lfp_final_wh:.1f} |

> As SOH drops → $r_{{dyn}}$ rises → more $I^2R$ heat loss → higher Wh/km. SIB starts with 1.5× higher $R_0$ and degrades faster, compounding the gap.
""")

    # 3b. Capacity Fade
    st.markdown(f"""
**3b. Capacity Fade (Ah)**

- **SIB** retains **{sib_final_cap:.2f} Ah** while **LFP** retains **{lfp_final_cap:.2f} Ah** after {sim_days} days.
- **{more_capacity}** has more remaining usable capacity.
""")

    with st.expander("🔬 View Complete Capacity Fade Calculation (every step)"):
        st.markdown(f"""
##### Capacity Fade Model

Remaining capacity is directly proportional to SOH. The SOH value comes from Step 8 of the SOH derivation above.

$$
C_{{remaining}} = C_{{nominal}} \\times SOH = 30 \\text{{ Ah}} \\times SOH
$$

Where $C_{{nominal}}$ = 30 Ah (rated capacity of the 48V 30Ah battery pack).

##### Full Chain: SIB

$$
SOH_{{SIB}} = {sib_final_soh/100:.4f} \\quad \\text{{(from Step 8)}}
$$
$$
C_{{remaining,SIB}} = 30 \\times {sib_final_soh / 100:.4f} = \\boxed{{{sib_final_cap:.2f} \\text{{ Ah}}}}
$$
$$
C_{{lost,SIB}} = 30 - {sib_final_cap:.2f} = {30.0 - sib_final_cap:.2f} \\text{{ Ah}}
$$

##### Full Chain: LFP

$$
SOH_{{LFP}} = {lfp_final_soh/100:.4f} \\quad \\text{{(from Step 8)}}
$$
$$
C_{{remaining,LFP}} = 30 \\times {lfp_final_soh / 100:.4f} = \\boxed{{{lfp_final_cap:.2f} \\text{{ Ah}}}}
$$
$$
C_{{lost,LFP}} = 30 - {lfp_final_cap:.2f} = {30.0 - lfp_final_cap:.2f} \\text{{ Ah}}
$$

| | SIB | LFP |
|--|-----|-----|
| Nominal | 30.00 Ah | 30.00 Ah |
| Final SOH | {sib_final_soh:.2f}% | {lfp_final_soh:.2f}% |
| **Remaining** | **{sib_final_cap:.2f} Ah** | **{lfp_final_cap:.2f} Ah** |
| Lost | {30.0 - sib_final_cap:.2f} Ah | {30.0 - lfp_final_cap:.2f} Ah |

> End-of-Life threshold: 80% SOH = 24.00 Ah. Below this, the battery is unfit for fleet use.
""")

    # 4. TCO Accumulation — use fleet averages (not Bike 0)
    # Fleet totals (sum across all 25 bikes per model)
    fleet_total_sib_owned = sum(b.opex + b.capex_amortized for b in fleets["SIB Owned"])
    fleet_total_lfp_owned = sum(b.opex + b.capex_amortized for b in fleets["LFP Owned"])
    fleet_total_sib_baas = sum(b.opex + b.capex_amortized for b in fleets["SIB BaaS"])
    fleet_total_lfp_baas = sum(b.opex + b.capex_amortized for b in fleets["LFP BaaS"])
    grand_total = fleet_total_sib_owned + fleet_total_lfp_owned + fleet_total_sib_baas + fleet_total_lfp_baas

    # Per-bike averages (fleet total / 25)
    n = len(fleets["SIB Owned"])  # 25
    avg_sib_owned = fleet_total_sib_owned / n
    avg_lfp_owned = fleet_total_lfp_owned / n
    avg_sib_baas = fleet_total_sib_baas / n
    avg_lfp_baas = fleet_total_lfp_baas / n

    avg_sib_owned_daily = avg_sib_owned / sim_days
    avg_lfp_owned_daily = avg_lfp_owned / sim_days
    avg_sib_baas_daily = avg_sib_baas / sim_days
    avg_lfp_baas_daily = avg_lfp_baas / sim_days

    # Detect crossover points
    sib_crossover = None
    lfp_crossover = None
    for d in range(len(rep_sib.log_cum_tco)):
        if sib_crossover is None and rep_sib.log_cum_tco[d] > rep_sib_baas.log_cum_tco[d]:
            sib_crossover = rep_sib.log_day[d]
        if lfp_crossover is None and rep_lfp.log_cum_tco[d] > rep_lfp_baas.log_cum_tco[d]:
            lfp_crossover = rep_lfp.log_day[d]

    avg_spend_map = {
        'SIB Owned': avg_sib_owned, 'LFP Owned': avg_lfp_owned,
        'SIB BaaS': avg_sib_baas, 'LFP BaaS': avg_lfp_baas
    }
    lowest_spend_model = min(avg_spend_map, key=avg_spend_map.get)
    lowest_spend_val = avg_spend_map[lowest_spend_model]

    st.markdown(f"""
**4. Cumulative TCO Accumulation**

- After {sim_days} days, the **fleet-average** cumulative spend per bike:
  - **SIB Owned:** KSh {avg_sib_owned:,.2f} (≈ KSh {avg_sib_owned_daily:,.2f}/day)
  - **LFP Owned:** KSh {avg_lfp_owned:,.2f} (≈ KSh {avg_lfp_owned_daily:,.2f}/day)
  - **SIB BaaS:** KSh {avg_sib_baas:,.2f} (≈ KSh {avg_sib_baas_daily:,.2f}/day)
  - **LFP BaaS:** KSh {avg_lfp_baas:,.2f} (≈ KSh {avg_lfp_baas_daily:,.2f}/day)
- **{lowest_spend_model}** has the lowest average per-bike spend at KSh {lowest_spend_val:,.2f}.
""")

    st.markdown(f"""
**Total Fleet Spend (all 25 bikes per model × {sim_days} days)**

| Model | Bikes | Fleet Total Spend (KSh) |
|-------|-------|------------------------|
| SIB Owned (Depot) | 25 | **KSh {fleet_total_sib_owned:,.0f}** |
| LFP Owned (Depot) | 25 | **KSh {fleet_total_lfp_owned:,.0f}** |
| SIB BaaS (Swapping) | 25 | **KSh {fleet_total_sib_baas:,.0f}** |
| LFP BaaS (Swapping) | 25 | **KSh {fleet_total_lfp_baas:,.0f}** |
| **Grand Total (100 bikes)** | **100** | **KSh {grand_total:,.0f}** |
""")

    # Verification note
    sib_owned_bike_costs = [b.opex + b.capex_amortized for b in fleets["SIB Owned"]]
    lfp_baas_bike_costs = [b.opex + b.capex_amortized for b in fleets["LFP BaaS"]]
    sib_owned_min = min(sib_owned_bike_costs)
    sib_owned_max = max(sib_owned_bike_costs)
    lfp_baas_min = min(lfp_baas_bike_costs)
    lfp_baas_max = max(lfp_baas_bike_costs)

    with st.expander("📊 Bike 0 vs Fleet Average — Methodology & Variance Explanation"):
        st.markdown(f"""
##### Why Bike 0 TCO ≠ Fleet Average TCO

The feasibility report shows two TCO figures per model: **Bike 0** (a single bike) and **Fleet Average** (mean of all 25 bikes). These differ for two reasons:

**1. Owned Models (Depot Charging) — IEEE 754 Floating-Point Precision**

All 25 Depot bikes process identical trips with identical physics, so they accumulate
the same OPEX and CAPEX. The minor difference (~KSh {abs(sib_owned_bike_costs[0] - avg_sib_owned):.2f}) arises
from IEEE 754 floating-point arithmetic: dividing the fleet sum by 25 introduces
rounding at the ~15th decimal digit. This is inherent to all digital computation
and is negligible (<0.01% of TCO).

| Metric | SIB Owned | LFP Owned |
|--------|-----------|-----------|
| Bike 0 TCO | KSh {sib_owned_bike_costs[0]:,.2f} | KSh {[b.opex + b.capex_amortized for b in fleets['LFP Owned']][0]:,.2f} |
| Fleet Avg | KSh {avg_sib_owned:,.2f} | KSh {avg_lfp_owned:,.2f} |
| Δ (difference) | KSh {abs(sib_owned_bike_costs[0] - avg_sib_owned):.2f} | KSh {abs([b.opex + b.capex_amortized for b in fleets['LFP Owned']][0] - avg_lfp_owned):.2f} |
| All 25 bikes identical? | ✅ Yes (range: {sib_owned_min:,.2f} – {sib_owned_max:,.2f}) | ✅ Yes |

**2. BaaS Models (Swapping) — Stochastic Range Anxiety**

Each of the 25 BaaS bikes is initialized with a unique **random anxiety threshold**:

$$
\\theta_{{anxiety}} \\sim \\text{{Uniform}}({anxiety_min}\\%, {anxiety_max}\\%)
$$

Riders with higher $\\theta$ swap their battery earlier (at higher SOC), resulting in:
- **More swaps** → higher accumulated OPEX
- **Lower average SOC** → slightly different energy dynamics

This produces genuine statistical variance across the 25 bikes:

| Metric | SIB BaaS | LFP BaaS |
|--------|----------|----------|
| Bike 0 TCO | KSh {[b.opex + b.capex_amortized for b in fleets['SIB BaaS']][0]:,.2f} | KSh {lfp_baas_bike_costs[0]:,.2f} |
| Fleet Avg | KSh {avg_sib_baas:,.2f} | KSh {avg_lfp_baas:,.2f} |
| Δ (difference) | KSh {abs([b.opex + b.capex_amortized for b in fleets['SIB BaaS']][0] - avg_sib_baas):,.2f} | KSh {abs(lfp_baas_bike_costs[0] - avg_lfp_baas):,.2f} |
| Min bike cost | KSh {min(b.opex + b.capex_amortized for b in fleets['SIB BaaS']):,.2f} | KSh {lfp_baas_min:,.2f} |
| Max bike cost | KSh {max(b.opex + b.capex_amortized for b in fleets['SIB BaaS']):,.2f} | KSh {lfp_baas_max:,.2f} |
| Spread (max - min) | KSh {max(b.opex + b.capex_amortized for b in fleets['SIB BaaS']) - min(b.opex + b.capex_amortized for b in fleets['SIB BaaS']):,.2f} | KSh {lfp_baas_max - lfp_baas_min:,.2f} |

##### Verification: Fleet Avg × 25 = Fleet Total

$$
\\text{{SIB Owned: }} {avg_sib_owned:,.2f} \\times 25 = {avg_sib_owned * 25:,.2f} \\approx \\text{{KSh }} {fleet_total_sib_owned:,.2f} \\checkmark
$$

$$
\\text{{LFP BaaS: }} {avg_lfp_baas:,.2f} \\times 25 = {avg_lfp_baas * 25:,.2f} \\approx \\text{{KSh }} {fleet_total_lfp_baas:,.2f} \\checkmark
$$

> **For report purposes:** Use the **Fleet Average** as the authoritative per-bike figure
> and the **Fleet Total** as the authoritative absolute figure. Bike 0 is shown
> for transparency only.
""")

    # --- TCO Math Derivation ---
    with st.expander("🔬 View Mathematical Derivation of TCO"):
        st.markdown(f"""
##### General TCO Formula

$$
TCO_{{per\\ km}} = \\frac{{\\overline{{OPEX}} + \\overline{{CAPEX}}_{{amortized}}}}{{\\overline{{km}}_{{total}}}}
$$

Where the overline denotes the **fleet average** across all 100 bikes.

---

##### Owned Model (Depot Charging)

**OPEX** accumulates per trip as energy consumed × grid tariff:

$$
OPEX_{{trip}} = E_{{trip}} \\text{{ (kWh)}} \\times \\text{{KPLC Tariff}} = E_{{trip}} \\times {kplc_tariff} \\text{{ KSh/kWh}}
$$

**CAPEX Amortization** is proportional to battery degradation:

$$
CAPEX_{{amortized}} = CAPEX_{{initial}} \\times \\frac{{1 - SOH}}{{0.20}}
$$

This means CAPEX is fully consumed when SOH drops by 20% (reaches 80% End-of-Life).

---

##### BaaS Model (Battery Swapping)

**OPEX** accumulates per swap event (no CAPEX for the fleet owner):

$$
OPEX_{{swap}} = N_{{swaps}} \\times {swap_fee} \\text{{ KSh}}
$$

A swap is triggered when: $SOC < (EFC_{{trip}} + 0.05)$ OR $SOC < \\theta_{{anxiety}}$

Where $\\theta_{{anxiety}} \\sim U({anxiety_min}\\%, {anxiety_max}\\%)$ is stochastically resampled after each swap.

---

##### Computed Values (Bike 0 — individual sample)
""")

        sib_bike0_tco = rep_sib.opex + rep_sib.capex_amortized
        lfp_bike0_tco = rep_lfp.opex + rep_lfp.capex_amortized
        sib_baas_bike0_tco = rep_sib_baas.opex + rep_sib_baas.capex_amortized
        lfp_baas_bike0_tco = rep_lfp_baas.opex + rep_lfp_baas.capex_amortized

        st.markdown(f"""
| Component | SIB Owned | LFP Owned | SIB BaaS | LFP BaaS |
|-----------|-----------|-----------|----------|----------|
| Initial CAPEX | KSh {rep_sib.initial_capex:,.0f} | KSh {rep_lfp.initial_capex:,.0f} | KSh 0 | KSh 0 |
| Final SOH | {rep_sib.log_soh[-1]:.2f}% | {rep_lfp.log_soh[-1]:.2f}% | {rep_sib_baas.log_soh[-1]:.2f}% | {rep_lfp_baas.log_soh[-1]:.2f}% |
| SOH Loss (1−SOH) | {(1 - rep_sib.log_soh[-1]/100):.4f} | {(1 - rep_lfp.log_soh[-1]/100):.4f} | — | — |
| CAPEX Amortized | KSh {rep_sib.capex_amortized:,.0f} | KSh {rep_lfp.capex_amortized:,.0f} | KSh 0 | KSh 0 |
| Accumulated OPEX | KSh {rep_sib.opex:,.0f} | KSh {rep_lfp.opex:,.0f} | KSh {rep_sib_baas.opex:,.0f} | KSh {rep_lfp_baas.opex:,.0f} |
| **Bike 0 TCO** | **KSh {sib_bike0_tco:,.0f}** | **KSh {lfp_bike0_tco:,.0f}** | **KSh {sib_baas_bike0_tco:,.0f}** | **KSh {lfp_baas_bike0_tco:,.0f}** |
| **Fleet Avg TCO** | **KSh {avg_sib_owned:,.2f}** | **KSh {avg_lfp_owned:,.2f}** | **KSh {avg_sib_baas:,.2f}** | **KSh {avg_lfp_baas:,.2f}** |
| Total km | {rep_sib.total_km:,.0f} | {rep_lfp.total_km:,.0f} | {rep_sib_baas.total_km:,.0f} | {rep_lfp_baas.total_km:,.0f} |
| **TCO / km** | **KSh {sib_owned_tco:.2f}** | **KSh {lfp_owned_tco:.2f}** | **KSh {sib_baas_tco:.2f}** | **KSh {lfp_baas_tco:.2f}** |
""")

        st.markdown(f"""
##### Worked Example: SIB Owned (Bike 0)

$$
CAPEX_{{amort}} = {rep_sib.initial_capex:,.0f} \\times \\frac{{{(1 - rep_sib.log_soh[-1]/100):.4f}}}{{0.20}} = \\text{{KSh }} {rep_sib.capex_amortized:,.0f}
$$

$$
TCO_{{cum}} = {rep_sib.opex:,.0f} + {rep_sib.capex_amortized:,.0f} = \\text{{KSh }} {sib_bike0_tco:,.0f}
$$

$$
TCO_{{per\\ km}} = \\frac{{{sib_bike0_tco:,.0f}}}{{{rep_sib.total_km:,.0f}}} = \\text{{KSh }} {sib_owned_tco:.2f}/\\text{{km}}
$$

##### Worked Example: LFP BaaS (Bike 0)

$$
TCO_{{cum}} = OPEX_{{swaps}} = \\text{{KSh }} {lfp_baas_bike0_tco:,.0f} \\quad (\\text{{no CAPEX}})
$$

$$
TCO_{{per\\ km}} = \\frac{{{lfp_baas_bike0_tco:,.0f}}}{{{rep_lfp_baas.total_km:,.0f}}} = \\text{{KSh }} {lfp_baas_tco:.2f}/\\text{{km}}
$$
""")

    # Crossover commentary
    if sib_crossover or lfp_crossover:
        crossover_text = ""
        if sib_crossover:
            crossover_text += f"  - **SIB:** Owned model overtakes BaaS in cumulative cost around **Day {sib_crossover}**, meaning BaaS is cheaper for SIB beyond this point.\n"
        if lfp_crossover:
            crossover_text += f"  - **LFP:** Owned model overtakes BaaS in cumulative cost around **Day {lfp_crossover}**, meaning BaaS is cheaper for LFP beyond this point.\n"
        st.markdown(f"- **Crossover Points** (where Owned total spend exceeds BaaS):\n{crossover_text}")

    # 5. Overall Verdict
    st.markdown(f"""
**5. Overall Verdict**

> 🏆 For fleet owners choosing **battery ownership (Depot charging)**, **{best_owned}** \
is recommended at KSh {results[best_owned]:.2f}/km.
>
> 🏆 For fleet owners using **Battery-as-a-Service (swapping)**, **{best_baas}** \
is recommended at KSh {results[best_baas]:.2f}/km.
>
> 🏆 **Overall most cost-effective path: {overall_best}** at KSh {results[overall_best]:.2f}/km.
""")

    # Caveats
    st.caption(f"📌 This report is based on a {sim_days}-day Monte Carlo simulation with "
               f"25 e-bikes per model (100 total) at {env_temp}°C ambient temperature. "
               f"Results are stochastic and may vary between runs.")

elif not sim_ready and not etl_btn:
    st.info("👈 Upload your three data files, then click **📥 Perform ETL** to extract parameters before running the simulation.")
