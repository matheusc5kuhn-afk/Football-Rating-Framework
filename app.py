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
TOURNAMENTS_FILE = "tournaments.csv"
STATS_FILE = "stats.json"

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
        # Ensure Tournament column exists
        if 'Tournament' not in df.columns:
            df['Tournament'] = ""
        return df
    return pd.DataFrame({"Match ID": [1], "Date": [pd.Timestamp(datetime.now())], "Opponent": ["Team A"], "Venue": ["Home"], "Result": ["W 2-1"], "Player": ["Player 1"], "Tournament": [""]})

def load_tournaments():
    if os.path.exists(TOURNAMENTS_FILE):
        df = pd.read_csv(TOURNAMENTS_FILE)
        df['Date Added'] = pd.to_datetime(df['Date Added'], format='mixed')
        return df
    return pd.DataFrame({
        "Tournament ID": pd.Series([], dtype='int64'),
        "Name": pd.Series([], dtype='str'),
        "Date Added": pd.Series([], dtype='datetime64[ns]')
    })

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            data = json.load(f)
            for key in data:
                if 'Timestamp' in data[key]:
                    data[key]['Timestamp'] = datetime.fromisoformat(data[key]['Timestamp'])
            return data
    return {}

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

def save_tournaments(df):
    df.to_csv(TOURNAMENTS_FILE, index=False)

def save_stats(data):
    data_to_save = {}
    for key in data:
        data_to_save[key] = data[key].copy()
        if 'Timestamp' in data_to_save[key]:
            data_to_save[key]['Timestamp'] = data_to_save[key]['Timestamp'].isoformat()
    with open(STATS_FILE, 'w') as f:
        json.dump(data_to_save, f)

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

if 'tournaments' not in st.session_state:
    st.session_state.tournaments = load_tournaments()

if 'stats' not in st.session_state:
    st.session_state.stats = load_stats()

if 'match_mprs' not in st.session_state:
    st.session_state.match_mprs = load_mprs()

# Initialize general MPR list if not exists
if 'general_mprs' not in st.session_state:
    st.session_state.general_mprs = []

# --- TABS ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "1. Players", 
    "2. Tournaments", 
    "3. Matches",
    "4. Action Log (CAV)", 
    "5. Match Rating (MPR)", 
    "6. MPR History", 
    "7. Player Stats",
    "8. Season (CSR)"
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

# --- TAB 2: TOURNAMENT MANAGEMENT ---
with tab2:
    st.header("Tournament Management")
    
    st.subheader("Add New Tournament")
    col1, col2 = st.columns(2)
    
    with col1:
        new_tournament_name = st.text_input("Tournament Name")
    with col2:
        if st.button("➕ Add Tournament"):
            if new_tournament_name:
                max_id = st.session_state.tournaments["Tournament ID"].max() if len(st.session_state.tournaments) > 0 else 0
                new_row = pd.DataFrame([{
                    "Tournament ID": int(max_id + 1),
                    "Name": new_tournament_name,
                    "Date Added": datetime.now()
                }])
                st.session_state.tournaments = pd.concat([st.session_state.tournaments, new_row], ignore_index=True)
                save_tournaments(st.session_state.tournaments)
                st.success(f"✓ Tournament '{new_tournament_name}' added!")
                st.rerun()
    
    st.divider()
    st.markdown("#### Manage Tournaments")
    
    col_config = {
        "Tournament ID": st.column_config.NumberColumn("Tournament ID", width="small"),
        "Name": st.column_config.TextColumn("Name", width="large"),
        "Date Added": st.column_config.DatetimeColumn("Date Added", width="medium")
    }
    
    edited_tournaments = st.data_editor(
        st.session_state.tournaments,
        column_config=col_config,
        num_rows="dynamic",
        use_container_width=True,
        key="tournaments_editor"
    )
    
    st.session_state.tournaments = edited_tournaments
    save_tournaments(st.session_state.tournaments)
    st.caption(f"📊 Total Tournaments: {len(st.session_state.tournaments)}")
    
    st.divider()
    st.markdown("#### Matches in Each Tournament")
    
    if len(st.session_state.tournaments) > 0 and len(st.session_state.matches) > 0:
        for idx, tournament in st.session_state.tournaments.iterrows():
            tournament_name = tournament['Name']
            tournament_matches = st.session_state.matches[st.session_state.matches["Tournament"] == tournament_name]
            
            with st.expander(f"📋 {tournament_name} ({len(tournament_matches)} matches)"):
                if len(tournament_matches) > 0:
                    matches_display = tournament_matches[["Match ID", "Date", "Opponent", "Venue", "Result"]].copy()
                    st.dataframe(matches_display, use_container_width=True)
                else:
                    st.info("No matches added to this tournament yet.")
    elif len(st.session_state.tournaments) > 0:
        st.info("No matches created yet. Add matches in the 'Matches' tab and link them to tournaments.")

# --- TAB 3: MATCH MANAGEMENT ---
with tab3:
    st.header("Match Management")
    
    st.subheader("Add New Match")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        new_match_date = st.date_input("Match Date", key="match_date_input")
    with col2:
        new_opponent = st.text_input("Opponent Team", key="match_opponent_input")
    with col3:
        new_venue = st.selectbox("Venue", ["Home", "Away", "Neutral"], key="match_venue_select")
    with col4:
        new_result = st.text_input("Result (e.g., W 2-1)", placeholder="W 2-1", key="match_result_input")
    with col5:
        tournament_options = st.session_state.tournaments["Name"].tolist() if len(st.session_state.tournaments) > 0 else []
        new_tournament = st.selectbox("Tournament (Optional)", options=["None"] + tournament_options, key="match_tournament_select")
    
    if st.button("➕ Add Match", key="add_match_btn"):
        if new_opponent and new_result:
            max_id = st.session_state.matches["Match ID"].max() if len(st.session_state.matches) > 0 else 0
            new_row = pd.DataFrame([{
                "Match ID": int(max_id + 1),
                "Date": pd.Timestamp(new_match_date),
                "Opponent": new_opponent,
                "Venue": new_venue,
                "Result": new_result,
                "Player": st.session_state.players["Player Name"].iloc[0] if len(st.session_state.players) > 0 else "Player 1",
                "Tournament": new_tournament if new_tournament != "None" else ""
            }])
            st.session_state.matches = pd.concat([st.session_state.matches, new_row], ignore_index=True)
            save_matches(st.session_state.matches)
            st.success(f"✓ Match vs {new_opponent} added!")
            st.rerun()
    
    st.divider()
    st.markdown("#### Manage Matches")
    
    # Ensure Date column is properly typed for data_editor
    st.session_state.matches['Date'] = pd.to_datetime(st.session_state.matches['Date'])
    
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
            width="medium"
        ),
        "Tournament": st.column_config.SelectboxColumn(
            "Tournament",
            options=[""] + st.session_state.tournaments["Name"].tolist() if len(st.session_state.tournaments) > 0 else [""],
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

# --- TAB 4: ACTION LOGGING (Multiple Rows) ---
with tab4:
    st.header("Match Action Log")
    st.markdown("Log every meaningful decision point to generate match aggregates.")
    
    st.subheader("Optional: Match Context")
    col_context_player, col_context_match = st.columns(2)
    
    with col_context_player:
        tab4_player = st.selectbox(
            "Player (for context)",
            options=["None"] + st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["None"],
            key="tab4_player_select"
        )
    
    with col_context_match:
        tab4_matches = []
        if len(st.session_state.matches) > 0:
            tab4_matches = [f"Match {int(row['Match ID'])} - {row['Date']} vs {row['Opponent']}" for _, row in st.session_state.matches.iterrows()]
        
        tab4_match = st.selectbox(
            "Match (for context)",
            options=["None"] + tab4_matches if tab4_matches else ["None"],
            key="tab4_match_select"
        )
    
    st.divider()

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

# --- TAB 5: MATCH RATING (MPR) ---
with tab5:
    st.header("Match Performance Rating (MPR)")
    st.markdown("Calculates both **MPR** (Role-Neutral) and **Weighted MPR** (Role-Specific).")
    
    # Role Selection
    selected_role = st.selectbox("Select Role for Weighting", list(ROLE_WEIGHTS.keys()))
    weights = ROLE_WEIGHTS[selected_role]
    st.divider()
    st.subheader("Optional: Link to Match for Auto-Calculated Modifiers")
    
    col_player_select, col_match_select = st.columns(2)
    
    with col_player_select:
        tab5_player = st.selectbox(
            "Player (for stats lookup)",
            options=["None"] + st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["None"]
        )
    
    with col_match_select:
        tab5_matches = []
        if tab5_player != "None" and len(st.session_state.matches) > 0:
            tab5_matches = [f"Match {int(row['Match ID'])} - {row['Date']} vs {row['Opponent']}" for _, row in st.session_state.matches.iterrows()]
        
        tab5_match = st.selectbox(
            "Match (for OM lookup)",
            options=["None"] + tab5_matches if tab5_matches else ["None"],
            key="tab5_match_select"
        )
    
    st.divider()
    
    
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
        
        # Auto-calculate or allow manual OM entry
        om_default = 1.0
        if tab5_player != "None" and tab5_match != "None":
            try:
                match_id = int(tab5_match.split(" ")[1])
                stats_key = f"{tab5_player}_m_{match_id}"
                if stats_key in st.session_state.stats:
                    goals = st.session_state.stats[stats_key].get("Goals", 0)
                    assists = st.session_state.stats[stats_key].get("Assists", 0)
                    om_default = 1.0 + (goals * 0.1) + (assists * 0.05)
                    om_default = min(om_default, 1.5)  # Cap at 1.5
                    st.info(f"📊 Auto-calculated OM from stats ({goals}G, {assists}A)", icon="ℹ️")
            except:
                pass
        
        om_in = st.number_input("OM (Outcome Multiplier)", 0.5, 1.5, value=om_default, step=0.1, help="Goal/Assist Context")
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

# --- TAB 6: MPR HISTORY ---
with tab6:
    st.header("Match Performance Rating (MPR) History")
    st.markdown("Add and manage individual player performance ratings linked to tournaments.")
    
    st.divider()
    st.subheader("Add New MPR Rating")
    
    col_select, col_player = st.columns(2)
    
    with col_select:
        tournament_options = st.session_state.tournaments["Name"].tolist() if len(st.session_state.tournaments) > 0 else []
        if not tournament_options:
            st.warning("⚠️ No tournaments created yet. Create one in the 'Tournaments' tab first.")
        tournament_context = st.selectbox(
            "Link to Tournament", 
            options=tournament_options if tournament_options else ["No tournaments available"]
        )
    
    with col_player:
        selected_player = st.selectbox(
            "Player",
            options=st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["N/A"]
        )
    
    col_role, col_om = st.columns(2)
    
    with col_role:
        mpr_role = st.selectbox("Player Role", list(ROLE_WEIGHTS.keys()), key="mpr_role_select")
    
    # Get match-specific stats to auto-calculate OM
    col_match_select, col_om_calc = st.columns(2)
    
    with col_match_select:
        # Get matches in the selected tournament
        tournament_matches = []
        if tournament_context != "No tournaments available" and len(st.session_state.matches) > 0:
            filtered = st.session_state.matches[st.session_state.matches["Tournament"] == tournament_context]
            if len(filtered) > 0:
                tournament_matches = [f"Match {int(row['Match ID'])} - {row['Date']} vs {row['Opponent']}" for _, row in filtered.iterrows()]
        
        selected_match_label = st.selectbox(
            "Link to Specific Match (Optional)", 
            options=["None"] + tournament_matches if tournament_matches else ["None"]
        )
    
    with col_om_calc:
        # Auto-calculate OM from stats if match selected
        om_base = 1.0
        if selected_match_label != "None":
            # Extract Match ID from label
            try:
                match_id = int(selected_match_label.split(" ")[1])
                stats_key = f"{selected_player}_m_{match_id}"
                if stats_key in st.session_state.stats:
                    goals = st.session_state.stats[stats_key].get("Goals", 0)
                    assists = st.session_state.stats[stats_key].get("Assists", 0)
                    om_base = 1.0 + (goals * 0.1) + (assists * 0.05)
                    om_base = min(om_base, 1.5)  # Cap at 1.5
            except:
                pass
        
        mpr_om = st.number_input("OM (Outcome Multiplier)", 0.5, 1.5, value=om_base, step=0.1, key="mpr_om")
    
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
                "Tournament": tournament_context if tournament_context != "No tournaments available" else None,
                "Match": selected_match_label if selected_match_label != "None" else None,
                "AQC": mpr_aqc,
                "HIS": mpr_his,
                "EC": mpr_ec,
                "TII": mpr_tii,
                "IBI": mpr_ibi,
                "OM": mpr_om,
                "MPR": mpr_value,
                "Timestamp": datetime.now()
            })
            st.success(f"✓ MPR {mpr_value:.1f} saved for {selected_player} in {tournament_context}!")
            st.rerun()
    
    st.divider()
    
    # Show MPR History
    if len(st.session_state.general_mprs) > 0:
        st.subheader("All MPR Ratings")
        
        mprs_df = pd.DataFrame(st.session_state.general_mprs)
        mprs_df = mprs_df[["Player", "Tournament", "Match", "Role", "AQC", "HIS", "EC", "TII", "IBI", "OM", "MPR", "Timestamp"]]
        
        st.dataframe(mprs_df, use_container_width=True)
        
        # Manage (delete) MPR History entries
        st.markdown("### Manage MPR History")
        options = []
        for i, item in enumerate(st.session_state.general_mprs):
            ts = item.get("Timestamp")
            try:
                ts_str = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts_str = str(ts)
            label = f"{i}: {item.get('Player','?')} | {item.get('Role','')} | {item.get('Tournament','')} | MPR {item.get('MPR',0):.1f} @ {ts_str}"
            options.append(label)

        to_delete = st.multiselect("Select MPRs to delete", options, key="mpr_delete_select")
        if st.button("Delete selected MPRs"):
            if not to_delete:
                st.warning("No MPRs selected for deletion.")
            else:
                selected_indices = [int(item.split(":" )[0]) for item in to_delete]
                for idx in sorted(selected_indices, reverse=True):
                    st.session_state.general_mprs.pop(idx)
                st.success(f"Deleted {len(selected_indices)} MPR(s).")
                st.rerun()

        col_avg, col_max, col_min, col_count = st.columns(4)
        col_avg.metric("Avg MPR", f"{mprs_df['MPR'].mean():.1f}")
        col_max.metric("Peak MPR", f"{mprs_df['MPR'].max():.1f}")
        col_min.metric("Min MPR", f"{mprs_df['MPR'].min():.1f}")
        col_count.metric("Total Ratings", f"{len(mprs_df)}")
    else:
        st.info("No MPRs recorded yet. Add one above to get started!")

# --- TAB 7: PLAYER STATS ---
with tab7:
    st.header("Player Statistics")
    st.markdown("Track player stats (Goals, Assists, BCC, Dribbles) that contribute to OM calculation.")
    
    st.divider()
    st.subheader("Add New Stats Record")
    
    col_type = st.columns(3)
    with col_type[0]:
        stats_scope = st.selectbox("Record Stats For", ["Match", "Tournament"], key="stats_scope")
    
    if stats_scope == "Match":
        col_player_stat, col_match_stat = st.columns(2)
        
        with col_player_stat:
            stat_player = st.selectbox(
                "Player",
                options=st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["N/A"],
                key="stat_player_select"
            )
        
        with col_match_stat:
            if len(st.session_state.matches) > 0:
                match_options = [f"Match {int(row['Match ID'])} - {row['Date']} vs {row['Opponent']}" for _, row in st.session_state.matches.iterrows()]
            else:
                match_options = ["No matches available"]
            
            stat_match_label = st.selectbox(
                "Match",
                options=match_options,
                key="stat_match_select"
            )
        stat_tournament_label = None
    else:
        col_player_stat, col_tourn_stat = st.columns(2)
        
        with col_player_stat:
            stat_player = st.selectbox(
                "Player",
                options=st.session_state.players["Player Name"].tolist() if len(st.session_state.players) > 0 else ["N/A"],
                key="stat_player_select_t"
            )
        
        with col_tourn_stat:
            tournament_options = st.session_state.tournaments["Name"].tolist() if len(st.session_state.tournaments) > 0 else []
            stat_tournament_label = st.selectbox(
                "Tournament",
                options=tournament_options if tournament_options else ["No tournaments available"],
                key="stat_tournament_select"
            )
        stat_match_label = None
    
    col_stats = st.columns(4)
    
    with col_stats[0]:
        stat_goals = st.number_input("Goals", 0, key="stat_goals")
    with col_stats[1]:
        stat_assists = st.number_input("Assists", 0, key="stat_assists")
    with col_stats[2]:
        stat_bcc = st.number_input("BCC (Big Chances Created)", 0, key="stat_bcc")
    with col_stats[3]:
        stat_dribbles = st.number_input("Dribbles", 0, key="stat_dribbles")
    
    st.divider()
    st.subheader("Team & Clutch Context")
    
    col_team = st.columns(4)
    
    with col_team[0]:
        stat_team_goals = st.number_input("Team Goals (Total)", 0, key="stat_team_goals")
    with col_team[1]:
        stat_clutch_ga = st.number_input("Clutch G/A (Player)", 0, key="stat_clutch_ga")
    with col_team[2]:
        stat_team_clutch_ga = st.number_input("Team Clutch G/A", 0, key="stat_team_clutch_ga")
    with col_team[3]:
        st.empty()
    
    if st.button("💾 Save Stats"):
        if (stats_scope == "Match" and stat_match_label != "No matches available") or (stats_scope == "Tournament" and stat_tournament_label != "No tournaments available"):
            try:
                if stats_scope == "Match":
                    match_id = int(stat_match_label.split(" ")[1])
                    stats_key = f"{stat_player}_m_{match_id}"
                    context_desc = f"Match {match_id}"
                else:
                    stats_key = f"{stat_player}_t_{stat_tournament_label}"
                    context_desc = f"Tournament {stat_tournament_label}"
                
                st.session_state.stats[stats_key] = {
                    "Player": stat_player,
                    "Match ID": int(stat_match_label.split(" ")[1]) if stats_scope == "Match" else None,
                    "Tournament": stat_tournament_label if stats_scope == "Tournament" else None,
                    "Goals": stat_goals,
                    "Assists": stat_assists,
                    "BCC": stat_bcc,
                    "Dribbles": stat_dribbles,
                    "Team Goals": int(stat_team_goals),
                    "Clutch G/A": int(stat_clutch_ga),
                    "Team Clutch G/A": int(stat_team_clutch_ga),
                    "Timestamp": datetime.now()
                }
                
                save_stats(st.session_state.stats)
                st.success(f"✓ Stats saved for {stat_player} in {context_desc}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving stats: {e}")
        else:
            st.warning("No matches available. Create a match first.")
    
    st.divider()
    st.subheader("All Stats Records")
    
    if len(st.session_state.stats) > 0:
        # Convert stats to DataFrame for display
        stats_list = []
        for key, value in st.session_state.stats.items():
            stats_list.append(value)
        
        stats_df = pd.DataFrame(stats_list)
        # Ensure all required columns exist
        required_cols = ["Player", "Match ID", "Tournament", "Goals", "Assists", "BCC", "Dribbles", "Team Goals", "Clutch G/A", "Team Clutch G/A", "Timestamp"]
        for col in required_cols:
            if col not in stats_df.columns:
                stats_df[col] = 0 if col != "Tournament" else ""

        # Add Type column to distinguish match vs tournament
        stats_df["Type"] = stats_df.apply(
            lambda row: "Tournament" if pd.notna(row["Tournament"]) and row["Tournament"] != "" else "Match",
            axis=1
        )
        
        # Calculate contributions
        stats_df["G/A"] = stats_df["Goals"] + stats_df["Assists"]
        stats_df["Team Contribution"] = stats_df.apply(
            lambda row: f"{(row['G/A'] / row['Team Goals'] * 100):.1f}%" if row['Team Goals'] > 0 else "N/A",
            axis=1
        )
        stats_df["Clutch Contribution"] = stats_df.apply(
            lambda row: f"{(row['Clutch G/A'] / row['Team Clutch G/A'] * 100):.1f}%" if row['Team Clutch G/A'] > 0 else "N/A",
            axis=1
        )
        
        display_cols = ["Type", "Player", "Match ID", "Tournament", "Goals", "Assists", "BCC", "Dribbles", "Team Contribution", "Clutch Contribution"]
        stats_df = stats_df[display_cols]
        stats_df = stats_df.sort_values("Timestamp", ascending=False)
        
        st.dataframe(stats_df, use_container_width=True)
        
        # Manage (delete) stats
        st.markdown("### Manage Stats Records")
        options = []
        for key in st.session_state.stats:
            item = st.session_state.stats[key]
            ts = item.get("Timestamp")
            try:
                ts_str = ts.strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts_str = str(ts)
            goals = item.get("Goals", 0)
            assists = item.get("Assists", 0)
            match_id = item.get("Match ID")
            tournament = item.get("Tournament")
            if tournament and tournament != "":
                context_label = f"Tournament {tournament}"
            elif match_id:
                context_label = f"Match {int(match_id)}"
            else:
                context_label = "Unknown"
            label = f"{item.get('Player','')} | {context_label} | G:{goals} A:{assists} @ {ts_str}"
            options.append((label, key))

        to_delete = st.multiselect(
            "Select stats to delete",
            options=[opt[0] for opt in options],
            key="stats_delete_select"
        )
        
        if st.button("Delete selected stats"):
            if not to_delete:
                st.warning("No stats selected for deletion.")
            else:
                selected_keys = [opt[1] for opt in options if opt[0] in to_delete]
                for key in selected_keys:
                    del st.session_state.stats[key]
                save_stats(st.session_state.stats)
                st.success(f"Deleted {len(selected_keys)} stat record(s).")
                st.rerun()
        
        # Summary stats
        col_total_goals, col_total_assists, col_total_bcc, col_total_dribbles = st.columns(4)
        col_total_goals.metric("Total Goals", f"{stats_df['Goals'].sum()}")
        col_total_assists.metric("Total Assists", f"{stats_df['Assists'].sum()}")
        col_total_bcc.metric("Total BCC", f"{stats_df['BCC'].sum()}")
        col_total_dribbles.metric("Total Dribbles", f"{stats_df['Dribbles'].sum()}")
        
        st.divider()
        st.subheader("Contribution Summary")
        col_contrib_avg, col_clutch_avg, col_total_ga = st.columns(3)
        
        # Calculate average team contribution (excluding "N/A" values)
        numeric_contrib = []
        for contrib in stats_df["Team Contribution"]:
            try:
                numeric_contrib.append(float(contrib.rstrip('%')))
            except:
                pass
        avg_team_contrib = np.mean(numeric_contrib) if numeric_contrib else 0
        
        # Calculate average clutch contribution
        numeric_clutch = []
        for contrib in stats_df["Clutch Contribution"]:
            try:
                numeric_clutch.append(float(contrib.rstrip('%')))
            except:
                pass
        avg_clutch_contrib = np.mean(numeric_clutch) if numeric_clutch else 0
        
        col_contrib_avg.metric("Avg Team Contribution", f"{avg_team_contrib:.1f}%")
        col_clutch_avg.metric("Avg Clutch Contribution", f"{avg_clutch_contrib:.1f}%")
        col_total_ga.metric("Total G/A", f"{(stats_df['Goals'].sum() + stats_df['Assists'].sum())}")
    else:
        st.info("No stats recorded yet. Add one above to get started!")

# --- TAB 8: SEASON EVALUATION (CSR) ---
with tab8:
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

