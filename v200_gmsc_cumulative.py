import pandas as pd
import numpy as np
import os

def process_player_cumulative_gmsc_v108():
    input_file = "nba_player_single_game_gmsc_v52.csv"
    output_file = "nba_player_cumulative_gmsc_v108.csv"

    print(f"--- 開始執行 v108 (part 1)：計算球員累積 GmSc ---")
    
    if not os.path.exists(input_file):
        print(f"錯誤: 找不到輸入檔案 '{input_file}'。")
        return

    df = pd.read_csv(input_file)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Single_Game_GmSc'] = pd.to_numeric(df['Single_Game_GmSc'], errors='coerce').fillna(0.0)
    df = df.sort_values(by=['Player_ID', 'Date']).reset_index(drop=True)

    # 計算累積
    df['Player_Cumulative_GmSc'] = df.groupby(['Player_ID', 'Season_Year'])['Single_Game_GmSc'].cumsum()
    
    # 計算賽前
    df['Before_Game_Player_GmSc'] = df.groupby(['Player_ID', 'Season_Year'])['Player_Cumulative_GmSc'].shift(1).fillna(0.0)
    
    # 過濾日期
    start_date = pd.to_datetime('2015-10-01')
    df = df[df['Date'] >= start_date].copy()

    final_columns = ['Player_ID', 'Player_Name', 'Season_Year', 'Date', 'Team_Abbr', 'Before_Game_Player_GmSc']
    df[final_columns].to_csv(output_file, index=False)
    print(f"成功儲存: {output_file}")

if __name__ == "__main__":
    process_player_cumulative_gmsc_v108()