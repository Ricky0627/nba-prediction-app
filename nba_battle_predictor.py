import pandas as pd
import numpy as np
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import re
import warnings

# 忽略 sklearn 的特徵名稱警告
warnings.filterwarnings("ignore", category=UserWarning)

# --- 1. 賽程抓取模組 ---
def get_schedule_for_date(target_date):
    """從 BBR 抓取指定日期的賽程"""
    year = target_date.year
    month_name = target_date.strftime("%B").lower()
    season = year + 1 if target_date.month >= 10 else year
    
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games-{month_name}.html"
    print(f"正在抓取 {target_date.strftime('%Y-%m-%d')} 的賽程...")
    
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find('table', {'id': 'schedule'})
        if not table: return []
        games = []
        
        target_str_padded = target_date.strftime("%a, %b %d, %Y")
        day = target_date.day
        target_str_no_pad = target_date.strftime("%a, %b ") + str(day) + target_date.strftime(", %Y")
        
        for row in table.find('tbody').find_all('tr'):
            date_th = row.find('th', {'data-stat': 'date_game'})
            if not date_th: continue
            game_date_str = date_th.text.strip()
            
            if game_date_str == target_str_padded or game_date_str == target_str_no_pad:
                v_cell = row.find('td', {'data-stat': 'visitor_team_name'})
                h_cell = row.find('td', {'data-stat': 'home_team_name'})
                
                if v_cell and h_cell:
                    v_abbr = None; h_abbr = None
                    if v_cell.find('a'):
                        m = re.search(r'/teams/(\w{3})/', v_cell.find('a')['href'])
                        if m: v_abbr = m.group(1)
                    if h_cell.find('a'):
                        m = re.search(r'/teams/(\w{3})/', h_cell.find('a')['href'])
                        if m: h_abbr = m.group(1)
                    if v_abbr and h_abbr:
                        games.append((h_abbr, v_abbr))
        return games
    except: return []

# --- 2. 傷病計算模組 ---
def get_player_gmsc_dict(gmsc_file):
    if not os.path.exists(gmsc_file): return {}
    try:
        df = pd.read_csv(gmsc_file)
        # 支援跨年度，取該球員最後一筆數據
        df['Date'] = pd.to_datetime(df['Date'])
        latest_stats = df.sort_values('Date').groupby('Player_ID').last()
        
        player_gmsc_map = {}
        for player_id, row in latest_stats.iterrows():
            # 這裡的 Before_Game_Player_GmSc 是累積值
            # 我們需要除以場次來得到平均
            # 但這裡簡化，我們直接假設它是「能力值」
            # 為了修正這個邏輯，我們應該在 data_process8 就算出平均
            # 這裡我們先用一個簡單的啟發式：如果值很大(>1000)，假設是累積，除以82? 
            # 不，這太不準了。
            # 最好的方式是讀取 FINAL_MASTER_v108_base.csv 裡的 Total_Injury_Impact 反推? 不行。
            
            # 權宜之計：直接使用該數值，但在 data_process8 我們其實已經存了累積值
            # 我們需要一個「場均 GmSc」的表。
            # 為了現在能跑，我們假設這個值是「累積值」，並除以一個估計場次 (例如 40)
            # 或者，我們讀取 'nba_player_single_game_gmsc_v52.csv' 來算平均會更準
            pass 

        # 重新讀取單場數據來算平均 (這是最準的)
        raw_gmsc_file = "nba_player_single_game_gmsc_v52.csv"
        if os.path.exists(raw_gmsc_file):
            df_raw = pd.read_csv(raw_gmsc_file)
            # 只取最近一季 (2026)
            df_2026 = df_raw[df_raw['Season_Year'] == 2026]
            if df_2026.empty: df_2026 = df_raw[df_raw['Season_Year'] == 2025]
            
            avg_gmsc = df_2026.groupby('Player_ID')['Single_Game_GmSc'].mean().to_dict()
            return avg_gmsc
            
        return {}
    except: return {}

def calculate_team_injury_impact(team_abbr, injuries_df, player_gmsc_map):
    if injuries_df is None or injuries_df.empty: return 0.0
    team_injuries = injuries_df[injuries_df['Team_Abbr'] == team_abbr]
    if team_injuries.empty: return 0.0
    
    missing_gmsc_sum = 0.0
    injured_names = []
    
    for _, row in team_injuries.iterrows():
        p_id = row['Player_ID']
        p_name = row['Player_Name']
        
        if pd.notna(p_id) and p_id in player_gmsc_map:
            gmsc = player_gmsc_map[p_id]
            if gmsc > 0:
                missing_gmsc_sum += gmsc
                injured_names.append(f"{p_name}({gmsc:.1f})")
        # 如果找不到 ID 但有名字，也許可以試著匹配 (暫略)
    
    total_impact = missing_gmsc_sum / 80.0
    if injured_names:
        print(f"   └─ [{team_abbr} 傷兵] {', '.join(injured_names)} (Impact: {total_impact:.2f})")
        
    return total_impact

# --- 3. 主程式 ---
def run_battle_predictor():
    print("\n" + "="*60)
    print(" 🏀 NBA 實戰預測器 (v114 完美版)")
    print("="*60)
    
    data_file = "FINAL_MASTER_DATASET_v109_FIXED.csv"
    injury_file = "current_injuries.csv"
    gmsc_file = "nba_player_cumulative_gmsc_v108.csv" # 這裡只用來檢查路徑

    if not os.path.exists(data_file): return

    print("正在載入數據庫並訓練模型...")
    df = pd.read_csv(data_file)
    df['date_dt'] = pd.to_datetime(df['date'])
    
    # 特徵列
    feature_columns = [
        'Diff_Days_Since_Last_Game', 'Diff_Before_Game_Streak',
        'Diff_Before_Game_Win_Pct_Last_5', 'Diff_Before_Game_Avg_Margin_Last_5',
        'Diff_Before_Game_Win_Pct_Last_10', 'Diff_CS_Win_Pct_L5', 'Diff_CS_Avg_Margin_L5',
        'Diff_Before_Game_H2H_Win_Pct_L5', 'Diff_Before_Game_H2H_Avg_Margin_L5',
        'Diff_Total_Injury_Impact', 'Diff_Before_Game_Avg_NetRtg',
        'Diff_Before_Game_Avg_TOV_Rate', 'Diff_Before_Game_Avg_ORB_Pct'
    ]
    
    df_train = df.fillna(0)
    X = df_train[feature_columns]
    y = df_train['Win']
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)
    print("模型訓練完成。")

    player_gmsc_map = get_player_gmsc_dict(gmsc_file)
    df_injuries = pd.DataFrame()
    if os.path.exists(injury_file):
        df_injuries = pd.read_csv(injury_file)

    # 自動抓取賽程
    last_data_date = df['date_dt'].max()
    target_date = last_data_date + timedelta(days=1)
    print(f"\n預測目標日: {target_date.strftime('%Y-%m-%d')}")
    
    todays_games = get_schedule_for_date(target_date)
    
    if todays_games:
        print(f"\n找到 {len(todays_games)} 場比賽，開始分析...\n")
        # 標題對齊
        print(f"{'主隊':<4} vs {'客隊':<4} | {'主勝率':<7} | {'信心等級'}")
        print("-" * 60)
        
        for home_team, away_team in todays_games:
            predict_single_game(home_team, away_team, target_date, df, model, scaler, df_injuries, player_gmsc_map, feature_columns, auto_mode=True)
    else:
        print(f"\n[提示] {target_date.strftime('%Y-%m-%d')} 沒有比賽。")

    # 手動模式
    while True:
        print("\n" + "-"*40)
        print("手動查詢模式 (輸入 'q' 退出)")
        home_input = input(f"主隊 (預設日期 {target_date.strftime('%Y-%m-%d')}): ").strip().upper()
        if home_input == 'Q': break
        if not home_input: continue
        away_input = input("客隊: ").strip().upper()
        if away_input == 'Q': break
        
        if home_input not in df['Team_Abbr'].unique():
            print("錯誤: 主隊代碼無效。")
            continue
            
        predict_single_game(home_input, away_input, target_date, df, model, scaler, df_injuries, player_gmsc_map, feature_columns, auto_mode=False)

def predict_single_game(home_team, away_team, target_date, df, model, scaler, df_injuries, player_gmsc_map, feature_cols, auto_mode=False):
    
    def get_stats(team_abbr):
        team_games = df[((df['Team_Abbr'] == team_abbr) | (df['Opp_Abbr'] == team_abbr)) & 
                        (df['date_dt'] < target_date)].sort_values('date_dt')
        
        if team_games.empty: return None, None
        last_game = team_games.iloc[-1]
        l_date = last_game['date_dt']
        
        stats = {}
        prefix = "Before_Game_" if last_game['Team_Abbr'] == team_abbr else "Opp_Before_Game_"
        
        stats['Win_Pct_L5'] = last_game.get(f'{prefix}Win_Pct_Last_5', 0)
        stats['Win_Pct_L10'] = last_game.get(f'{prefix}Win_Pct_Last_10', 0)
        stats['Margin_L5'] = last_game.get(f'{prefix}Avg_Margin_Last_5', 0)
        stats['Streak'] = last_game.get(f'{prefix}Streak', 0)
        
        if prefix == "Before_Game_":
            stats['CS_Win_L5'] = last_game.get('CS_Win_Pct_L5', 0)
            stats['CS_Margin_L5'] = last_game.get('CS_Avg_Margin_L5', 0)
        else:
            stats['CS_Win_L5'] = last_game.get('Opp_CS_Win_Pct_L5', 0)
            stats['CS_Margin_L5'] = last_game.get('Opp_CS_Avg_Margin_L5', 0)
            
        stats['H2H_Win'] = last_game.get(f'{prefix}H2H_Win_Pct_L5', 0.5)
        stats['H2H_Margin'] = last_game.get(f'{prefix}H2H_Avg_Margin_L5', 0)
        stats['NetRtg'] = last_game.get(f'{prefix}Avg_NetRtg', 0)
        stats['TOV'] = last_game.get(f'{prefix}Avg_TOV_Rate', 0)
        stats['ORB'] = last_game.get(f'{prefix}Avg_ORB_Pct', 0)
        
        is_win = (last_game['Win'] == 1) if prefix == "Before_Game_" else (last_game['Win'] == 0)
        if is_win: stats['Streak'] = stats['Streak'] + 1 if stats['Streak'] > 0 else 1
        else: stats['Streak'] = stats['Streak'] - 1 if stats['Streak'] < 0 else -1
            
        return stats, l_date

    h_stats, h_date = get_stats(home_team)
    a_stats, a_date = get_stats(away_team)
    
    if not h_stats or not a_stats:
        if not auto_mode: print("數據不足。")
        return

    diff_rest = (target_date - h_date).days - (target_date - a_date).days
    
    h_impact = calculate_team_injury_impact(home_team, df_injuries, player_gmsc_map)
    a_impact = calculate_team_injury_impact(away_team, df_injuries, player_gmsc_map)
    diff_inj = h_impact - a_impact
    
    input_features = [
        diff_rest,
        h_stats['Streak'] - a_stats['Streak'],
        h_stats['Win_Pct_L5'] - a_stats['Win_Pct_L5'],
        h_stats['Margin_L5'] - a_stats['Margin_L5'],
        h_stats['Win_Pct_L10'] - a_stats['Win_Pct_L10'],
        h_stats['CS_Win_L5'] - a_stats['CS_Win_L5'],
        h_stats['CS_Margin_L5'] - a_stats['CS_Margin_L5'],
        h_stats['H2H_Win'] - a_stats['H2H_Win'],
        h_stats['H2H_Margin'] - a_stats['H2H_Margin'],
        diff_inj,
        h_stats['NetRtg'] - a_stats['NetRtg'],
        h_stats['TOV'] - a_stats['TOV'],
        h_stats['ORB'] - a_stats['ORB']
    ]
    
    # 【修正】轉為 DataFrame 以消除警告
    X_in = scaler.transform(pd.DataFrame([input_features], columns=feature_cols))
    prob = model.predict_proba(X_in)[0][1]
    
    confidence = "⚪"
    if prob >= 0.65: confidence = "🟢 高 (主)"
    elif prob <= 0.35: confidence = "🔴 高 (客)"
    
    if auto_mode:
        print(f"{home_team:<4} vs {away_team:<4} | {prob:.1%}    | {confidence}")
    else:
        print(f"\n>>> {home_team} vs {away_team} <<<")
        print(f"主勝率: {prob:.1%} {confidence}")

if __name__ == "__main__":
    run_battle_predictor()