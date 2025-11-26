import pandas as pd
import numpy as np
import os

def update_team_advanced_stats_v53():
    """
    【v1 (v53版) - 更新球隊進階數據】
    輸入: nba_game_data_raw_v52_PATCHED.csv
    輸出: v1_adv_stats_v53.csv
    """
    print("--- 開始執行 v200 (第 6a 步)：更新進階數據 (v53) ---")

    # 1. 輸入檔案：您剛剛修補好的 PATCHED 檔案
    input_file = "nba_game_data_raw_v52_PATCHED.csv"
    output_file = "v1_adv_stats_v53.csv"

    if not os.path.exists(input_file):
        print(f"錯誤：找不到 '{input_file}'。")
        return

    print(f"正在讀取 '{input_file}'...")
    df = pd.read_csv(input_file)

    # 2. 計算單場進階數據 (Pace, Ratings)
    print("正在計算單場進階數據...")
    df['home_poss'] = df['home_fga'] + 0.44 * df['home_fta'] - df['home_orb'] + df['home_tov']
    df['away_poss'] = df['away_fga'] + 0.44 * df['away_fta'] - df['away_orb'] + df['away_tov']
    df['pace'] = (df['home_poss'] + df['away_poss']) / 2

    df['home_off_rtg'] = (df['home_pts'] / df['pace']) * 100
    df['away_off_rtg'] = (df['away_pts'] / df['pace']) * 100
    df['home_def_rtg'] = df['away_off_rtg']
    df['away_def_rtg'] = df['home_off_rtg']
    df['home_net_rtg'] = df['home_off_rtg'] - df['home_def_rtg']
    df['away_net_rtg'] = df['away_off_rtg'] - df['away_def_rtg']

    # 計算四因子組件
    df['home_tov_rate'] = (df['home_tov'] / df['pace']) * 100
    df['away_tov_rate'] = (df['away_tov'] / df['pace']) * 100
    df['home_orb_pct'] = df['home_orb'] / (df['home_orb'] + df['away_drb'])
    df['away_orb_pct'] = df['away_orb'] / (df['away_orb'] + df['home_drb'])
    df['home_orb_pct'] = df['home_orb_pct'].fillna(0)
    df['away_orb_pct'] = df['away_orb_pct'].fillna(0)

    # 提取賽季
    df['game_date'] = pd.to_datetime(df['date'].astype(str), format='%Y%m%d')
    df['season_year'] = df['game_date'].apply(lambda x: x.year + 1 if x.month >= 10 else x.year)

    # 3. 重塑數據 (Melt)
    print("正在重塑數據...")
    home_cols = ['game_id', 'game_date', 'season_year', 'home_team', 'away_team',
                 'pace', 'home_off_rtg', 'home_def_rtg', 'home_net_rtg', 'home_tov_rate', 'home_orb_pct']
    away_cols = ['game_id', 'game_date', 'season_year', 'home_team', 'away_team',
                 'pace', 'away_off_rtg', 'away_def_rtg', 'away_net_rtg', 'away_tov_rate', 'away_orb_pct']

    home_df = df[home_cols].copy()
    home_df.rename(columns={
        'home_team': 'team', 'away_team': 'opponent',
        'home_off_rtg': 'off_rtg', 'home_def_rtg': 'def_rtg', 'home_net_rtg': 'net_rtg',
        'home_tov_rate': 'tov_rate', 'home_orb_pct': 'orb_pct'
    }, inplace=True)
    home_df['location'] = 'Home'

    away_df = df[away_cols].copy()
    away_df.rename(columns={
        'away_team': 'team', 'home_team': 'opponent',
        'away_off_rtg': 'off_rtg', 'away_def_rtg': 'def_rtg', 'away_net_rtg': 'net_rtg',
        'away_tov_rate': 'tov_rate', 'away_orb_pct': 'orb_pct'
    }, inplace=True)
    away_df['location'] = 'Away'

    team_game_df = pd.concat([home_df, away_df], ignore_index=True)
    team_game_df.sort_values(by=['team', 'game_date'], inplace=True)

    # 4. 計算賽前累積平均值 (Before_Game)
    print("正在計算賽前累積平均值 (Before_Game)...")
    adv_stats_cols = ['pace', 'off_rtg', 'def_rtg', 'net_rtg', 'tov_rate', 'orb_pct']
    new_col_names = [f'Before_Game_Avg_{col}' for col in adv_stats_cols]

    for col in new_col_names:
        team_game_df[col] = np.nan

    groups = team_game_df.groupby(['season_year', 'team'])
    for name, group in groups:
        expanding_mean = group[adv_stats_cols].expanding().mean()
        before_game_avg = expanding_mean.shift(1)
        group_indices = group.index
        team_game_df.loc[group_indices, new_col_names] = before_game_avg.values

    team_game_df[new_col_names] = team_game_df[new_col_names].fillna(0)

    # 5. 儲存
    team_game_df.to_csv(output_file, index=False)
    print(f"成功儲存 v53 進階數據到: '{output_file}'")

if __name__ == "__main__":
    update_team_advanced_stats_v53()