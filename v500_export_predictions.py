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
import time

# 忽略警告
warnings.filterwarnings("ignore")

# --- 1. 賽程抓取模組 ---
def get_schedule_for_date(target_date):
    """從 BBR 抓取指定日期的賽程"""
    year = target_date.year
    month_name = target_date.strftime("%B").lower()
    season = year + 1 if target_date.month >= 10 else year
    
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games-{month_name}.html"
    # print(f"正在抓取 {target_date.strftime('%Y-%m-%d')} 的賽程...")
    
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200: return []
        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find('table', {'id': 'schedule'})
        if not table: return []
        games = []
        
        # Windows 相容日期格式
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
        # 嘗試讀取單場數據來計算更準確的平均值
        if os.path.exists("nba_player_single_game_gmsc_v52.csv"):
            df_raw = pd.read_csv("nba_player_single_game_gmsc_v52.csv")
            df_2026 = df_raw[df_raw['Season_Year'] == 2026]
            if df_2026.empty: df_2026 = df_raw[df_raw['Season_Year'] == 2025]
            avg_map = df_2026.groupby('Player_ID')['Single_Game_GmSc'].mean().to_dict()
            return avg_map
        return {}
    except: return {}

def calculate_team_injury_impact(team_abbr, injuries_df, player_gmsc_map):
    if injuries_df is None or injuries_df.empty: return 0.0, []
    team_injuries = injuries_df[injuries_df['Team_Abbr'] == team_abbr]
    if team_injuries.empty: return 0.0, []
    
    missing_gmsc_sum = 0.0
    injured_names = []
    
    for _, row in team_injuries.iterrows():
        p_id = row['Player_ID']
        p_name = row['Player_Name']
        
        gmsc = 0.0
        if pd.notna(p_id) and p_id in player_gmsc_map:
            gmsc = player_gmsc_map[p_id]
        
        if gmsc == 0.0: gmsc = 5.0 # 預設值
            
        if gmsc > 0:
            missing_gmsc_sum += gmsc
            injured_names.append(f"{p_name}({gmsc:.1f})")
             
    total_impact = missing_gmsc_sum / 80.0
    return total_impact, injured_names

# --- 3. 主程式 ---
def main():
    print("\n" + "="*60)
    print(" 🏀 NBA 每日賽事預測匯出工具 (v500 - 修正版)")
    print("="*60)
    
    # 1. 檔案路徑
    data_file = "FINAL_MASTER_DATASET_v109_FIXED.csv"
    injury_file = "current_injuries.csv"
    gmsc_file = "nba_player_cumulative_gmsc_v108.csv"

    if not os.path.exists(data_file):
        print(f"錯誤: 找不到 '{data_file}'")
        return

    # 2. 訓練模型
    print("正在訓練模型 (v114)...")
    df = pd.read_csv(data_file)
    df['date_dt'] = pd.to_datetime(df['date'])
    
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

    # 3. 準備傷病數據
    player_gmsc_map = get_player_gmsc_dict(gmsc_file)
    df_injuries = pd.DataFrame()
    if os.path.exists(injury_file):
        df_injuries = pd.read_csv(injury_file)
        print(f"已載入傷病名單 ({len(df_injuries)} 人)。")

    # 4. 智慧搜尋下一個比賽日
    last_data_date = df['date_dt'].max()
    start_search_date = last_data_date + timedelta(days=1)
    
    print(f"\n數據庫最後日期: {last_data_date.strftime('%Y-%m-%d')}")
    print("正在搜尋最近的比賽日 (最多往後 7 天)...")
    
    target_date = None
    todays_games = []
    
    for i in range(7):
        check_date = start_search_date + timedelta(days=i)
        check_date_str = check_date.strftime('%Y-%m-%d')
        
        print(f"  檢查 {check_date_str} ...", end=" ", flush=True)
        games = get_schedule_for_date(check_date)
        
        if games:
            print(f"✅ 發現 {len(games)} 場比賽！")
            target_date = check_date
            todays_games = games
            break
        else:
            print("❌ 無比賽")
            time.sleep(1)

    if not target_date:
        print("\n[警告] 未來 7 天內找不到任何比賽。")
        return

    target_date_str = target_date.strftime('%Y-%m-%d')
    print(f"\n鎖定預測日期: {target_date_str}")
    print("-" * 55)

    # 5. 批量預測與儲存
    export_data = []
    
    print(f"{'主隊':<5} vs {'客隊':<5} | {'主勝率':<8} | {'信心等級'}")
    print("-" * 55)

    for home, away in todays_games:
        # 獲取數據
        def get_stats(team_abbr):
            team_games = df[((df['Team_Abbr'] == team_abbr) | (df['Opp_Abbr'] == team_abbr)) & 
                            (df['date_dt'] < target_date)].sort_values('date_dt')
            if team_games.empty: return None
            last_game = team_games.iloc[-1]
            
            stats = {}
            prefix = "Before_Game_" if last_game['Team_Abbr'] == team_abbr else "Opp_Before_Game_"
            
            stats['Win_Pct_Last_5'] = last_game.get(f'{prefix}Win_Pct_Last_5', 0)
            stats['Win_Pct_Last_10'] = last_game.get(f'{prefix}Win_Pct_Last_10', 0)
            # 【修正】統一使用 Margin_L5
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
            
            stats['Last_Date'] = last_game['date_dt']
            return stats

        h_stats = get_stats(home)
        a_stats = get_stats(away)
        
        if not h_stats or not a_stats:
            print(f"跳過 {home} vs {away} (數據不足)")
            continue

        diff_rest = (target_date - h_stats['Last_Date']).days - (target_date - a_stats['Last_Date']).days
        
        h_impact, h_inj_names = calculate_team_injury_impact(home, df_injuries, player_gmsc_map)
        a_impact, a_inj_names = calculate_team_injury_impact(away, df_injuries, player_gmsc_map)
        diff_inj = h_impact - a_impact
        
        features = [
            diff_rest,
            h_stats['Streak'] - a_stats['Streak'],
            h_stats['Win_Pct_Last_5'] - a_stats['Win_Pct_Last_5'],
            # 【使用修正後的 Margin_L5】
            h_stats['Margin_L5'] - a_stats['Margin_L5'],
            h_stats['Win_Pct_Last_10'] - a_stats['Win_Pct_Last_10'],
            h_stats['CS_Win_L5'] - a_stats['CS_Win_L5'],
            h_stats['CS_Margin_L5'] - a_stats['CS_Margin_L5'],
            h_stats['H2H_Win'] - a_stats['H2H_Win'],
            h_stats['H2H_Margin'] - a_stats['H2H_Margin'],
            diff_inj,
            h_stats['NetRtg'] - a_stats['NetRtg'],
            h_stats['TOV'] - a_stats['TOV'],
            h_stats['ORB'] - a_stats['ORB']
        ]
        
        X_new = scaler.transform(pd.DataFrame([features], columns=feature_columns))
        prob = model.predict_proba(X_new)[0][1]
        
        confidence = "⚪"
        if prob >= 0.65: confidence = "🟢 High (Home)"
        elif prob <= 0.35: confidence = "🔴 High (Away)"
        else: confidence = "Toss-up"

        export_data.append({
            'Date': target_date_str,
            'Home': home,
            'Away': away,
            'Home_Win_Prob': round(prob, 3),
            'Confidence': confidence,
            'Diff_NetRtg': round(h_stats['NetRtg'] - a_stats['NetRtg'], 2),
            'Diff_Injury': round(diff_inj, 2),
            'Diff_Streak': h_stats['Streak'] - a_stats['Streak'],
            'Home_Injuries': "; ".join(h_inj_names),
            'Away_Injuries': "; ".join(a_inj_names)
        })
        
        print(f"{home:<5} vs {away:<5} | {prob:.1%}    | {confidence}")

    if export_data:
        output_csv = f"predictions_{target_date_str}.csv"
        pd.DataFrame(export_data).to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"\n成功匯出預測結果至: {output_csv}")

if __name__ == "__main__":
    main()