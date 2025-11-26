import pandas as pd
import numpy as np
import os
import traceback

def create_final_dataset_v108():
    raw_games_file = "nba_game_data_raw_v52_PATCHED.csv"
    player_gmsc_file = "nba_player_cumulative_gmsc_v108.csv"
    output_file = "FINAL_MASTER_v108_base.csv"

    print(f"--- 開始執行 v108 (part 2)：計算傷病與基礎特徵 (保留原始數據版) ---")
    
    if not os.path.exists(raw_games_file) or not os.path.exists(player_gmsc_file):
        print(f"錯誤: 找不到輸入檔案。")
        return

    try:
        df_games = pd.read_csv(raw_games_file)
        df_player = pd.read_csv(player_gmsc_file)
    except Exception as e:
        print(f"讀取失敗: {e}")
        return

    # --- 預處理與計算 (保持不變) ---
    df_games['date'] = df_games['date'].astype(str)
    df_games['game_date'] = pd.to_datetime(df_games['date'], format='%Y%m%d')
    df_games['Season_Year'] = df_games['game_date'].apply(lambda x: x.year + 1 if x.month >= 10 else x.year)
    
    df_games['home_win'] = (df_games['home_pts'] > df_games['away_pts']).astype(int)
    df_games['home_margin'] = df_games['home_pts'] - df_games['away_pts']
    df_games['away_margin'] = -df_games['home_margin']
    
    home_df = df_games[['game_id', 'game_date', 'Season_Year', 'home_team', 'away_team', 'home_pts', 'away_pts', 'home_win', 'home_margin', 'home_dnp']].copy()
    home_df.columns = ['game_id', 'date', 'Season_Year', 'team', 'opponent', 'pts', 'opp_pts', 'win', 'margin', 'dnp']
    home_df['location'] = 'Home'
    
    away_df = df_games[['game_id', 'game_date', 'Season_Year', 'away_team', 'home_team', 'away_pts', 'home_pts', 'home_win', 'away_margin', 'away_dnp']].copy()
    away_df['win'] = 1 - away_df['home_win']
    away_df = away_df.drop(columns=['home_win'])
    away_df.columns = ['game_id', 'date', 'Season_Year', 'team', 'opponent', 'pts', 'opp_pts', 'margin', 'dnp', 'win']
    away_df['location'] = 'Away'
    
    df_team_games = pd.concat([home_df, away_df], ignore_index=True)
    df_team_games = df_team_games.sort_values(by=['team', 'date']).reset_index(drop=True)
    
    # 計算累積數據
    df_team_games['win_cumsum'] = df_team_games.groupby(['Season_Year', 'team'])['win'].cumsum()
    df_team_games['games_played'] = df_team_games.groupby(['Season_Year', 'team']).cumcount() + 1
    df_team_games['Before_Game_Win_Pct'] = df_team_games.groupby(['Season_Year', 'team'])['win_cumsum'].shift(1) / df_team_games.groupby(['Season_Year', 'team'])['games_played'].shift(1)
    df_team_games['Before_Game_Win_Pct'] = df_team_games['Before_Game_Win_Pct'].fillna(0.0)
    
    df_team_games['Before_Game_Total_Games'] = df_team_games.groupby(['Season_Year', 'team'])['games_played'].shift(1).fillna(0)
    
    df_team_games['margin_cumsum'] = df_team_games.groupby(['Season_Year', 'team'])['margin'].cumsum()
    df_team_games['Before_Game_Avg_Margin'] = df_team_games.groupby(['Season_Year', 'team'])['margin_cumsum'].shift(1) / df_team_games.groupby(['Season_Year', 'team'])['games_played'].shift(1)
    df_team_games['Before_Game_Avg_Margin'] = df_team_games['Before_Game_Avg_Margin'].fillna(0.0)
    
    df_team_games['win_home'] = np.where(df_team_games['location'] == 'Home', df_team_games['win'], 0)
    df_team_games['games_home'] = np.where(df_team_games['location'] == 'Home', 1, 0)
    df_team_games['win_away'] = np.where(df_team_games['location'] == 'Away', df_team_games['win'], 0)
    df_team_games['games_away'] = np.where(df_team_games['location'] == 'Away', 1, 0)
    
    df_team_games['Before_Home_Win_Pct'] = df_team_games.groupby(['Season_Year', 'team'])['win_home'].cumsum().shift(1) / df_team_games.groupby(['Season_Year', 'team'])['games_home'].cumsum().shift(1)
    df_team_games['Before_Away_Win_Pct'] = df_team_games.groupby(['Season_Year', 'team'])['win_away'].cumsum().shift(1) / df_team_games.groupby(['Season_Year', 'team'])['games_away'].cumsum().shift(1)
    df_team_games['Before_Home_Win_Pct'] = df_team_games['Before_Home_Win_Pct'].fillna(0.0)
    df_team_games['Before_Away_Win_Pct'] = df_team_games['Before_Away_Win_Pct'].fillna(0.0)
    
    g = df_team_games.groupby(['Season_Year', 'team'])['win']
    df_team_games['Before_Game_Win_Pct_Last_5'] = g.shift(1).rolling(5, min_periods=1).mean().fillna(0.0)
    df_team_games['Before_Game_Win_Pct_Last_10'] = g.shift(1).rolling(10, min_periods=1).mean().fillna(0.0)
    g_margin = df_team_games.groupby(['Season_Year', 'team'])['margin']
    df_team_games['Before_Game_Avg_Margin_Last_5'] = g_margin.shift(1).rolling(5, min_periods=1).mean().fillna(0.0)
    
    def calculate_streak(series):
        streaks = []
        current_streak = 0
        for result in series:
            streaks.append(current_streak)
            if result == 1: current_streak = current_streak + 1 if current_streak > 0 else 1
            else: current_streak = current_streak - 1 if current_streak < 0 else -1
        return pd.Series(streaks, index=series.index)
    df_team_games['Before_Game_Streak'] = df_team_games.groupby(['Season_Year', 'team'])['win'].apply(calculate_streak).reset_index(level=[0,1], drop=True)

    df_team_games['date'] = pd.to_datetime(df_team_games['date'])
    df_team_games['prev_date'] = df_team_games.groupby(['Season_Year', 'team'])['date'].shift(1)
    df_team_games['Days_Since_Last_Game'] = (df_team_games['date'] - df_team_games['prev_date']).dt.days.fillna(7)
    
    df_team_games['CS_Win_Pct_L5'] = df_team_games['Before_Game_Win_Pct_Last_5']
    df_team_games['CS_Avg_Margin_L5'] = df_team_games['Before_Game_Avg_Margin_Last_5']
    
    df_team_games = df_team_games.sort_values(by=['team', 'opponent', 'date'])
    g_h2h_win = df_team_games.groupby(['team', 'opponent'])['win']
    df_team_games['Before_Game_H2H_Win_Pct_L5'] = g_h2h_win.shift(1).rolling(5, min_periods=1).mean().fillna(0.5)
    g_h2h_margin = df_team_games.groupby(['team', 'opponent'])['margin']
    df_team_games['Before_Game_H2H_Avg_Margin_L5'] = g_h2h_margin.shift(1).rolling(5, min_periods=1).mean().fillna(0.0)
    
    # 計算傷病指標
    df_player['Date'] = pd.to_datetime(df_player['Date'])
    df_player = df_player.sort_values(['Player_ID', 'Date'])
    df_player['games_played'] = df_player.groupby(['Player_ID', 'Season_Year']).cumcount() + 1
    df_player['Before_Game_Player_Avg_GmSc'] = df_player['Before_Game_Player_GmSc'] / df_player['games_played'].shift(1).fillna(1)
    df_player['Before_Game_Player_Avg_GmSc'] = df_player['Before_Game_Player_Avg_GmSc'].fillna(0.0)
    
    avg_gmsc_by_season = df_player.groupby(['Season_Year', 'Player_Name'])['Before_Game_Player_Avg_GmSc'].mean().to_dict()
    
    def calculate_injury_impact_fast(row):
        dnp_str = row['dnp']
        if pd.isna(dnp_str) or dnp_str == "": return 0.0
        team_avg_gmsc = 80.0 
        dnp_list = [x.strip() for x in str(dnp_str).split(',')]
        total_missing_gmsc = 0.0
        season = row['Season_Year']
        for player_name in dnp_list:
            key = (season, player_name)
            if key in avg_gmsc_by_season:
                total_missing_gmsc += avg_gmsc_by_season[key]
        return total_missing_gmsc / team_avg_gmsc

    df_team_games['Total_Injury_Impact'] = df_team_games.apply(calculate_injury_impact_fast, axis=1)

    # --- 合併主客隊數據 ---
    df_home = df_team_games[df_team_games['location'] == 'Home'].copy()
    df_away = df_team_games[df_team_games['location'] == 'Away'].copy()
    
    # 定義需要保留的原始特徵 (Opp_ 開頭)
    # 【!! 修正 !!】 我們保留所有 Before_Game 特徵
    raw_cols = [
        'Before_Game_Win_Pct', 'Before_Home_Win_Pct', 'Before_Away_Win_Pct', 
        'Before_Game_Avg_Margin', 'Before_Game_Streak', 
        'Before_Game_Win_Pct_Last_5', 'Before_Game_Win_Pct_Last_10', 
        'Before_Game_Avg_Margin_Last_5', 'CS_Win_Pct_L5', 'CS_Avg_Margin_L5',
        'Before_Game_H2H_Win_Pct_L5', 'Before_Game_H2H_Avg_Margin_L5',
        'Total_Injury_Impact', 'Days_Since_Last_Game', 'Before_Game_Total_Games'
    ]
    
    opp_cols = {col: f"Opp_{col}" for col in raw_cols}
    opp_cols['team'] = 'Opp_Abbr'
    
    df_away = df_away.rename(columns=opp_cols)
    
    df_final = pd.merge(df_home, df_away[['game_id'] + list(opp_cols.values())], on='game_id', how='inner')
    df_final.rename(columns={'team': 'Team_Abbr', 'opponent': 'Opp_Abbr', 'win': 'Win'}, inplace=True)
    
    # 計算 Diff
    diff_cols = [
        ('Diff_Before_Home_Win_Pct', 'Before_Home_Win_Pct', 'Opp_Before_Home_Win_Pct'), 
        ('Diff_Before_Away_Win_Pct', 'Before_Away_Win_Pct', 'Opp_Before_Away_Win_Pct'),
        ('Diff_Days_Since_Last_Game', 'Days_Since_Last_Game', 'Opp_Days_Since_Last_Game'),
        ('Diff_Before_Game_Streak', 'Before_Game_Streak', 'Opp_Before_Game_Streak'),
        ('Diff_Before_Game_Win_Pct_Last_5', 'Before_Game_Win_Pct_Last_5', 'Opp_Before_Game_Win_Pct_Last_5'),
        ('Diff_Before_Game_Avg_Margin_Last_5', 'Before_Game_Avg_Margin_Last_5', 'Opp_Before_Game_Avg_Margin_Last_5'),
        ('Diff_Before_Game_Win_Pct_Last_10', 'Before_Game_Win_Pct_Last_10', 'Opp_Before_Game_Win_Pct_Last_10'),
        ('Diff_CS_Win_Pct_L5', 'CS_Win_Pct_L5', 'Opp_CS_Win_Pct_L5'),
        ('Diff_CS_Avg_Margin_L5', 'CS_Avg_Margin_L5', 'Opp_CS_Avg_Margin_L5'),
        ('Diff_Before_Game_H2H_Win_Pct_L5', 'Before_Game_H2H_Win_Pct_L5', 'Opp_Before_Game_H2H_Win_Pct_L5'),
        ('Diff_Before_Game_H2H_Avg_Margin_L5', 'Before_Game_H2H_Avg_Margin_L5', 'Opp_Before_Game_H2H_Avg_Margin_L5'),
        ('Diff_Total_Injury_Impact', 'Total_Injury_Impact', 'Opp_Total_Injury_Impact')
    ]
    for new_col, home_col, opp_col in diff_cols:
        df_final[new_col] = df_final[home_col] - df_final[opp_col]

    df_final['date'] = df_final['date'].dt.strftime('%Y-%m-%d')

    # 【!! 修正 !!】 儲存時不篩選欄位，保留所有原始數據
    # 這樣 nba_battle_predictor 才能讀到 Before_Game_...
    df_final.to_csv(output_file, index=False)
    
    print(f"成功產生: {output_file} (共 {len(df_final)} 筆，包含原始數據)")

if __name__ == "__main__":
    create_final_dataset_v108()