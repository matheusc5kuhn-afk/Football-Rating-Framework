import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Football Performance Model",
    page_icon="⚽",
    layout="wide"
)

# --- DATA FILES ---
PLAYERS_FILE = "players.csv"
MATCHES_FILE = "matches.csv"
MPRS_FILE = "mprs.json"

def load_players():
    if os.path.exists(PLAYERS_FILE):
        df = pd.read_csv(PLAYERS_FILE)
        df['Date Added'] = pd.to_datetime(df['Date Added'], format='mixed')
        return df
    return pd.DataFrame({"Player Name": ["Player 1", "Player 2"], "Position": ["CM", "CF"], "Date Added": [datetime.now(), datetime.now()]})

def load_matches():
    if os.path.exists(MATCHES_FILE):
        df = pd.read_csv(MATCHES_FILE)
        df['Date'] = pd.to_datetime(df['Date'], format='mixed')
        return df
    return pd.DataFrame({"Match ID": [1], "Date": [datetime.now()], "Opponent": ["Team A"], "Venue": ["Home"], "Result": ["W 2-1"], "Player": ["Player 1"]})

def load_mprs():
    if os.path.exists(MPRS_FILE):
        with open(MPRS_FILE, 'r') as f:
            data = json.load(f)
            for key in data:
                for mpr in data[key]:
                    mpr['Timestamp'] = datetime.fromisoformat(mpr['Timestamp'])
            return data
    return {}

def save_players(df):
    df.to_csv(PLAYERS_FILE, index=False)

def save_matches(df):
    df.to_csv(MATCHES_FILE, index=False)

def save_mprs(data):
    data_to_save = {}
    for key in data:
        data_to_save[key] = []
        for mpr in data[key]:
            mpr_copy = mpr.copy()
            mpr_copy['Timestamp'] = mpr_copy['Timestamp'].isoformat()
            data_to_save[key].append(mpr_copy)
    with open(MPRS_FILE, 'w') as f:
        json.dump(data_to_save, f)

# --- ROLE PRESETS (Section 7) [cite: 83] ---
ROLE_WEIGHTS = {
    "CF / Striker": {"wAQC": 0.15, "wHIS": 0.35, "wEC": 0.10, "wTII": 0.10, "wIBI": 0.30},
    "Winger":       {"wAQC": 0.20, "wHIS": 0.30, "wEC": 0.15, "wTII": 0.10, "wIBI": 0.25},
    "AM / 10":      {"wAQC": 0.25, "wHIS": 0.25, "wEC": 0.15, "wTII": 0.15, "wIBI": 0.20},
    "CM / 8":       {"wAQC": 0.30, "wHIS": 0.15, "wEC": 0.30, "wTII": 0.20, "wIBI": 0.05},
    "DM / 6":       {"wAQC": 0.35, "wHIS": 0.10, "wEC": 0.35, "wTII": 0.25, "wIBI": 0.00},
}

# --- HELPER FUNCTIONS ---
def calculate_cav(row):
    """Calculates CAV based on Section 2.2 and applies Mistake Caps from Section 3.1"""
    # Base Formula [cite: 23]
    # CAV = (2·DQ + 2·EQ + 1.5·CD + 1.5·TA + 1·LOP) ÷ 8
    raw_score = (2 * row['DQ'] + 2 * row['EQ'] + 1.5 * row['CD'] + 1.5 * row['TA'] + 1 * row['LOP']) / 8
    
    # Mistake Doctrine (Caps) [cite: 27, 30]
    mistake = row['Mistake Type']
    cap = 10.0
    if mistake == "Type A (Decision)":
        cap = 4.0 # Cap for Incorrect decision
    elif mistake == "Type B (Execution)":
        cap = 8.3 # Cap for Correct decision, failed execution
    elif mistake == "Type C (Forced)":
        cap = 7.0 # Cap for Forced/contextual error
        
    return min(raw_score, cap)

# --- APP HEADER ---
st.title("Football Performance Model")
st.markdown("""
**Framework Basis**: Prioritizing decision quality, contextual correctness, and role responsibility.
""")

# --- INITIALIZE SESSION STATE ---
if 'players' not in st.session_state:
    st.session_state.players = load_players()

if 'matches' not in st.session_state:
    st.session_state.matches = load_matches()

if 'match_mprs' not in st.session_state:
    st.session_state.match_mprs = load_mprs()

# Initialize general MPR list if not exists
if 'general_mprs' not in st.session_state:
    st.session_state.general_mprs = []

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1. Players", 
    "2. Matches", 
    "3. Action Log (CAV)", 
    "4. Match Rating (MPR)", 
    "5. MPR History", 
    "6. Season (CSR)"
])

# --- TAB 1: PLAYER MANAGEMENT ---
with tab1:
    st.header("Player Management")
    
    col_add, col_info = st.columns([1, 2])
    
    with col_add:
        st.subheader("Add New Player")
        new_player_name = st.text_input("Player Name")
        new_player_pos = st.selectbox("Position", 
            ["CF / Striker", "Winger", "AM / 10", "CM / 8", "DM / 6", "LB", "CB", "RB", "GK"])
        
        if st.button("➕ Add Player"):
            if new_player_name:
                new_row = pd.DataFrame([{
                    "Player Name": new_player_name,
                    "Position": new_player_pos,
                    "Date Added": datetime.now()
                }])
                st.session_state.players = pd.concat([st.session_state.players, new_row], ignore_index=True)
                save_players(st.session_state.players)
                st.success(f"✓ {new_player_name} added!")
                st.rerun()
    
    with col_info:
        st.subheader("Active Players")
    
    # Display players table
    st.markdown("#### Manage Players")
    
    col_config = {
        "Player Name": st.column_config.TextColumn("Player Name", width="large"),
        "Position": st.column_config.SelectboxColumn(
            "Position",
            options=["CF / Striker", "Winger", "AM / 10", "CM / 8", "DM / 6", "LB", "CB", "RB", "GK"],
            width="medium"
        ),
        "Date Added": st.column_config.DatetimeColumn("Date Added", width="medium")
    }
    
    edited_players = st.data_editor(
        st.session_state.players,
        column_config=col_config,
        num_rows="dynamic",
        use_container_width=True,
        key="players_editor"
    )
    
    st.session_state.players = edited_players
    save_players(st.session_state.players)
    st.caption(f"📊 Total Players: {len(st.session_state.players)}")

# --- TAB 2: MATCH MANAGEMENT ---
with tab2:
    st.header("Match Management")
    
    st.subheader("Add New Match")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        new_match_date = st.date_input("Match Date")
    with col2:
        new_opponent = st.text_input("Opponent Team")
    with col3:
        new_venue = st.selectbox("Venue", ["Home", "Away", "Neutral"])
    with col4:
        new_result = st.text_input("Result (e.g., W 2-1)", placeholder="W 2-1")
    
    if st.button("➕ Add Match"):
        if new_opponent and new_result:
            max_id = st.session_state.matches["Match ID"].max() if len(st.session_state.matches) > 0 else 0
            new_row = pd.DataFrame([{
                "Match ID": int(max_id + 1),
                "Date": new_match_date,
                "Opponent": new_opponent,
                "Venue": new_venue,
                "Result": new_result,
                "Player": st.session_state.players["Player Name"].iloc[0] if len(st.session_state.players) > 0 else "Player 1"
            }])
            st.session_state.matches = pd.concat([st.session_state.matches, new_row], ignore_index=True)
            save_matches(st.session_state.matches)
            st.success(f"✓ Match vs {new_opponent} added!")
            st.rerun()
    
    st.divider()
    st.markdown("#### Manage Matches")
    
    col_config = {
        "Match ID": st.column_config.NumberColumn("Match ID", width="small"),
        "Date": st.column_config.DateColumn("Date", width="medium"),
        "Opponent": st.column_config.TextColumn("Opponent", width="large"),
        "Venue": st.column_config.SelectboxColumn(
            "Venue",
            options=["Home", "Away", "Neutral"],
            width="small"
        ),
        "Result": st.column_config.TextColumn("Result", width="medium"),
        "Player": st.column_config.SelectboxColumn(
            "Player",
            options=st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["N/A"],
            width="large"
        )
    }
    
    edited_matches = st.data_editor(
        st.session_state.matches,
        column_config=col_config,
        num_rows="dynamic",
        use_container_width=True,
        key="matches_editor"
    )
    
    st.session_state.matches = edited_matches
    save_matches(st.session_state.matches)
    st.caption(f"📊 Total Matches: {len(st.session_state.matches)}")

# --- TAB 3: ACTION LOGGING (Multiple Rows) ---
with tab3:
    st.header("Match Action Log")
    st.markdown("Log every meaningful decision point to generate match aggregates.")

    # Initialize Session State for Dataframe if not exists
    if 'match_data' not in st.session_state:
        # Start with empty dataframe
        st.session_state.match_data = pd.DataFrame({
            "Phase": [],
            "DQ": [],
            "EQ": [],
            "CD": [],
            "TA": [],
            "LOP": [],
            "Mistake Type": []
        })

    # Config for Data Editor
    column_config = {
        "Phase": st.column_config.SelectboxColumn(
            "Phase / Transition",
            options=["Build-up", "Final Third", "Attacking Transition", "Defensive Transition", "Set Piece"],
            required=True
        ),
        "DQ": st.column_config.NumberColumn("DQ (Decision)", min_value=1, max_value=10, step=0.5),
        "EQ": st.column_config.NumberColumn("EQ (Execution)", min_value=1, max_value=10, step=0.5),
        "CD": st.column_config.NumberColumn("CD (Difficulty)", min_value=1, max_value=10, step=0.5),
        "TA": st.column_config.NumberColumn("TA (Tactical)", min_value=1, max_value=10, step=0.5),
        "LOP": st.column_config.NumberColumn("LOP (Pressure)", min_value=1, max_value=10, step=0.5),
        "Mistake Type": st.column_config.SelectboxColumn(
            "Mistake Type",
            options=["None", "Type A (Decision)", "Type B (Execution)", "Type C (Forced)"],
            required=True
        )
    }

    # EDITABLE DATAFRAME
    edited_df = st.data_editor(
        st.session_state.match_data,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        key="editor"
    )

    # Calculate CAV for all rows
    if not edited_df.empty:
        # Apply calculation row by row
        edited_df['CAV'] = edited_df.apply(calculate_cav, axis=1)
        
        # Display aggregated metrics
        st.divider()
        st.subheader("Match Aggregates (Auto-Calculated)")
        
        col_a, col_b, col_c = st.columns(3)
        
        # 1. AQC (Average Quality of Choices) [cite: 35]
        aqc_val = edited_df['CAV'].mean()
        
        # 2. HIS (High-Impact Share) - % of actions >= 7.0 [cite: 35]
        high_impact_count = edited_df[edited_df['CAV'] >= 7.0].shape[0]
        total_actions = edited_df.shape[0]
        his_val = high_impact_count / total_actions if total_actions > 0 else 0.0
        
        # 3. Simple Consistency metric (for reference)
        # Using 1 - (StdDev / 10) as a proxy for EC
        std_dev = edited_df['CAV'].std()
        ec_est = 1.0 - (std_dev / 5.0) if total_actions > 1 else 1.0 # arbitrary scaling for visual reference
        ec_est = max(0.0, min(1.0, ec_est))

        col_a.metric("AQC (Avg CAV)", f"{aqc_val:.2f}", help="Mean of all CAVs (1-10)")
        col_b.metric("HIS (High Impact)", f"{his_val:.1%}", help="% of actions with CAV ≥ 7.0")
        col_c.metric("Actions Logged", f"{total_actions}")
        
        # Save to session state for Tab 4
        st.session_state.calculated_aqc = aqc_val
        st.session_state.calculated_his = his_val

# --- TAB 4: MATCH RATING (MPR) ---
with tab4:
    st.header("Match Performance Rating (MPR)")
    st.markdown("Calculates both **MPR** (Role-Neutral) and **Weighted MPR** (Role-Specific).")
    
    # Role Selection
    selected_role = st.selectbox("Select Role for Weighting", list(ROLE_WEIGHTS.keys()))
    weights = ROLE_WEIGHTS[selected_role]
    
    col_inputs, col_results = st.columns([1, 1])
    
    with col_inputs:
        st.subheader("1. Metric Inputs")
        
        # Auto-fill from Tab 3 if available
        def_aqc = st.session_state.get('calculated_aqc', 1.0)
        def_his = st.session_state.get('calculated_his', 0.0) * 100 # Convert to 0-100 scale for input
        
        # Inputs (Normalized to 0-100 scale where applicable per Section 6.2)
        aqc_in = st.number_input("AQC (Average Quality) [1-10]", value=float(def_aqc), min_value=1.0, max_value=10.0, format="%.2f")
        his_in = st.number_input("HIS (High Impact %) [0-100]", value=float(def_his), min_value=0.0, max_value=100.0)
        ec_in = st.number_input("EC (Consistency %) [0-100]", min_value=0.0, max_value=100.0, help="1 - Normalized Variance")
        tii_in = st.number_input("TII (Tactical Influence) [0-100]", step=5.0)
        ibi_in = st.number_input("IBI (Individual Brilliance) [0-100]", step=5.0)
        
        st.subheader("2. Modifiers")
        sci_in = st.slider("SCI (Stability Modifier)", 1.0, 1.08, 1.0, help="Capped at +8%")
        om_in = st.number_input("OM (Outcome Multiplier)", 0.5, 1.5, step=0.1, help="Goal/Assist Context")
        pi_in = st.number_input("PI (Presence Index)", 0.5, 1.5, step=0.1, help="Off-ball Gravity")

    # --- CALCULATIONS ---

    # 1. RAW MPR Calculation (Role Neutral) [cite: 36, 37, 44]
    # Formula: (60·(AQC/10) + 15·HIS + 10·(EC·SCI) + 8·TII + 6·IBI) × OM × PI
    # Note: The formula coefficients (60, 15, 10...) imply fractional inputs (0-1) for HIS/EC/TII/IBI.
    # We convert our 0-100 inputs back to decimals for this specific formula.
    
    raw_mpr_val = (
        60 * (aqc_in / 10) +
        15 * (his_in / 100) +
        10 * ((ec_in / 100) * sci_in) +
        8 * (tii_in / 100) +
        6 * (ibi_in / 100)
    ) * om_in * pi_in

    # 2. WEIGHTED MPR Calculation (Role Specific) [cite: 72, 73]
    # Formula uses normalized (0-100) inputs explicitly.
    aqc_n = aqc_in * 10 # Normalize AQC to 0-100
    
    weighted_sum = (
        weights['wAQC'] * aqc_n +
        weights['wHIS'] * his_in +
        weights['wEC'] * (ec_in * sci_in) +
        weights['wTII'] * tii_in +
        weights['wIBI'] * ibi_in
    )
    weighted_mpr_val = weighted_sum * om_in * pi_in

    with col_results:
        st.subheader("Match Results")
        
        # Comparison Metrics
        c1, c2 = st.columns(2)
        c1.metric("MPR (Role Neutral)", f"{raw_mpr_val:.1f}", help="Standard rating (0-100) regardless of role")
        c2.metric(f"Weighted MPR ({selected_role})", f"{weighted_mpr_val:.1f}", delta=f"{weighted_mpr_val - raw_mpr_val:.1f} vs Raw")
        
        st.caption("MPR measures a performance. Weighted MPR measures role-specific performance.")
        
        # Breakdown Chart
        st.markdown("#### Contribution Breakdown (Weighted)")
        chart_data = pd.DataFrame({
            "Component": ["AQC", "HIS", "EC", "TII", "IBI"],
            "Score Contribution": [
                weights['wAQC'] * aqc_n,
                weights['wHIS'] * his_in,
                weights['wEC'] * (ec_in * sci_in),
                weights['wTII'] * tii_in,
                weights['wIBI'] * ibi_in
            ]
        })
        st.bar_chart(chart_data, x="Component", y="Score Contribution")

# --- TAB 5: MPR HISTORY ---
with tab5:
    st.header("Match Performance Rating (MPR) History")
    st.markdown("Add and manage individual player performance ratings.")
    
    st.divider()
    st.subheader("Add New MPR Rating")
    
    col_select, col_player = st.columns(2)
    
    with col_select:
        # Optional match selection for context
        match_context = st.selectbox(
            "Link to Match (Optional)", 
            options=["None"] + st.session_state.matches.apply(
                lambda x: f"Match {int(x['Match ID'])} - {x['Date']} vs {x['Opponent']}", axis=1
            ).tolist() if len(st.session_state.matches) > 0 else ["None"]
        )
    
    with col_player:
        selected_player = st.selectbox(
            "Player",
            options=st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["N/A"]
        )
    
    col_role, col_om = st.columns(2)
    
    with col_role:
        mpr_role = st.selectbox("Player Role", list(ROLE_WEIGHTS.keys()), key="mpr_role_select")
    
    with col_om:
        mpr_om = st.number_input("OM (Outcome Multiplier)", 0.5, 1.5, step=0.1, key="mpr_om")
    
    col_inputs = st.columns(5)
    
    with col_inputs[0]:
        mpr_aqc = st.number_input("AQC", 1.0, 10.0, format="%.1f", key="mpr_aqc")
    with col_inputs[1]:
        mpr_his = st.number_input("HIS %", 0.0, 100.0, step=5.0, key="mpr_his")
    with col_inputs[2]:
        mpr_ec = st.number_input("EC %", 0.0, 100.0, step=5.0, key="mpr_ec")
    with col_inputs[3]:
        mpr_tii = st.number_input("TII %", 0.0, 100.0, step=5.0, key="mpr_tii")
    with col_inputs[4]:
        mpr_ibi = st.number_input("IBI %", 0.0, 100.0, step=5.0, key="mpr_ibi")
    
    # Calculate MPR
    weights = ROLE_WEIGHTS[mpr_role]
    aqc_n = mpr_aqc * 10
    weighted_sum = (
        weights['wAQC'] * aqc_n +
        weights['wHIS'] * mpr_his +
        weights['wEC'] * mpr_ec +
        weights['wTII'] * mpr_tii +
        weights['wIBI'] * mpr_ibi
    )
    mpr_value = weighted_sum * mpr_om
    
    col_calc, col_save = st.columns([1, 1])
    
    with col_calc:
        st.metric("Calculated Weighted MPR", f"{mpr_value:.1f}")
    
    with col_save:
        if st.button("💾 Save MPR"):
            st.session_state.general_mprs.append({
                "Player": selected_player,
                "Role": mpr_role,
                "Match": match_context if match_context != "None" else None,
                "AQC": mpr_aqc,
                "HIS": mpr_his,
                "EC": mpr_ec,
                "TII": mpr_tii,
                "IBI": mpr_ibi,
                "OM": mpr_om,
                "MPR": mpr_value,
                "Timestamp": datetime.now()
            })
            st.success(f"✓ MPR {mpr_value:.1f} saved for {selected_player}!")
            st.rerun()
    
    st.divider()
    
    # Show MPR History
    if len(st.session_state.general_mprs) > 0:
        st.subheader("All MPR Ratings")
        
        mprs_df = pd.DataFrame(st.session_state.general_mprs)
        mprs_df = mprs_df[["Player", "Match", "Role", "AQC", "HIS", "EC", "TII", "IBI", "OM", "MPR", "Timestamp"]]
        
        st.dataframe(mprs_df, use_container_width=True)
        
        col_avg, col_max, col_min, col_count = st.columns(4)
        col_avg.metric("Avg MPR", f"{mprs_df['MPR'].mean():.1f}")
        col_max.metric("Peak MPR", f"{mprs_df['MPR'].max():.1f}")
        col_min.metric("Min MPR", f"{mprs_df['MPR'].min():.1f}")
        col_count.metric("Total Ratings", f"{len(mprs_df)}")
    else:
        st.info("No MPRs recorded yet. Add one above to get started!")

# --- TAB 6: SEASON EVALUATION (CSR) ---
with tab6:
    st.header("Contextual Season Rating (CSR)")
    st.markdown("Automatically calculates season rating from stored MPRs.")
    
    # Collect all MPRs from general list
    if len(st.session_state.general_mprs) == 0:
        st.warning("⚠️ No MPRs recorded yet. Add ratings in the 'MPR History' tab first!")
    else:
        mprs_df = pd.DataFrame(st.session_state.general_mprs)
        
        col_auto, col_manual = st.columns([1, 1])
        
        with col_auto:
            st.subheader("Auto-Calculated (from MPR History)")
            
            avg_mpr = mprs_df['MPR'].mean()
            high_count = len(mprs_df[mprs_df['MPR'] >= 70])
            total_count = len(mprs_df)
            repeatability = (high_count / total_count * 100) if total_count > 0 else 0
            peak5 = mprs_df.nlargest(5, 'MPR')['MPR'].mean()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Avg_MPR", f"{avg_mpr:.1f}")
            m2.metric("Repeatability %", f"{repeatability:.0f}%", help="% of matches with MPR ≥ 70")
            m3.metric("Peak5 Avg", f"{peak5:.1f}")
            m4.metric("Matches", f"{total_count}")
            
            st.caption("These values are automatically calculated from your saved MPRs.")
        
        with col_manual:
            st.subheader("Manual Adjustments")
            
            role_transfer = st.number_input("Role Transferability Score (0-100)", 
                                           value=70.0, help="Scalability across systems/opponents")
        
        st.divider()
        
        # CSR Formula [cite: 96]
        # CSR = 0.45·Avg_MPR + 0.20·Repeatability + 0.15·RoleTransfer + 0.20·Peak5
        csr_score = (0.45 * avg_mpr) + (0.20 * repeatability) + (0.15 * role_transfer) + (0.20 * peak5)
        
        col_csr, col_breakdown = st.columns([1, 2])
        
        with col_csr:
            st.metric("📊 Final CSR Score", f"{csr_score:.1f}", delta=f"Peak: {peak5:.1f}")
        
        with col_breakdown:
            st.subheader("CSR Breakdown")
            breakdown_data = {
                "Component": ["Avg_MPR (45%)", "Repeatability (20%)", "Peak5 (20%)", "Role Transfer (15%)"],
                "Contribution": [
                    0.45 * avg_mpr,
                    0.20 * repeatability,
                    0.20 * peak5,
                    0.15 * role_transfer
                ]
            }
            breakdown_df = pd.DataFrame(breakdown_data)
            st.bar_chart(breakdown_df.set_index("Component"))
        
        st.divider()
        st.subheader("MPR Timeline")
        timeline_data = mprs_df.sort_values("Timestamp")
        st.line_chart(timeline_data.set_index("Timestamp")[["MPR"]])
        
        st.info("""
        **CSR Interpretation**
        * **Avg_MPR**: Average performance across all matches
        * **Repeatability**: Consistency (% of matches ≥ 70)
        * **Peak5**: Best 5 match average (ceiling)
        * **Role Transferability**: Flexibility across positions
        * **CSR**: Overall season quality score
        """)

