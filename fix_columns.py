import pandas as pd
import os

def run_fix_columns():
    print("--- 開始執行：修正欄位名稱 (含原始特徵) ---")

    input_file = "FINAL_MASTER_DATASET_v109.csv"
    output_file = "FINAL_MASTER_DATASET_v109_FIXED.csv"

    if not os.path.exists(input_file):
        print(f"錯誤: 找不到 '{input_file}'")
        return

    df = pd.read_csv(input_file)
    
    # 定義需要修正的欄位映射 (Diff 和 原始數據)
    rename_map = {
        # Diff
        'Diff_Before_Game_Avg_pace': 'Diff_Before_Game_Avg_Pace',
        'Diff_Before_Game_Avg_off_rtg': 'Diff_Before_Game_Avg_OffRtg',
        'Diff_Before_Game_Avg_def_rtg': 'Diff_Before_Game_Avg_DefRtg',
        'Diff_Before_Game_Avg_net_rtg': 'Diff_Before_Game_Avg_NetRtg',
        'Diff_Before_Game_Avg_tov_rate': 'Diff_Before_Game_Avg_TOV_Rate',
        'Diff_Before_Game_Avg_orb_pct': 'Diff_Before_Game_Avg_ORB_Pct',
        # Raw (Home)
        'Before_Game_Avg_pace': 'Before_Game_Avg_Pace',
        'Before_Game_Avg_off_rtg': 'Before_Game_Avg_OffRtg',
        'Before_Game_Avg_def_rtg': 'Before_Game_Avg_DefRtg',
        'Before_Game_Avg_net_rtg': 'Before_Game_Avg_NetRtg',
        'Before_Game_Avg_tov_rate': 'Before_Game_Avg_TOV_Rate',
        'Before_Game_Avg_orb_pct': 'Before_Game_Avg_ORB_Pct',
        # Raw (Opponent)
        'Opp_Before_Game_Avg_pace': 'Opp_Before_Game_Avg_Pace',
        'Opp_Before_Game_Avg_off_rtg': 'Opp_Before_Game_Avg_OffRtg',
        'Opp_Before_Game_Avg_def_rtg': 'Opp_Before_Game_Avg_DefRtg',
        'Opp_Before_Game_Avg_net_rtg': 'Opp_Before_Game_Avg_NetRtg',
        'Opp_Before_Game_Avg_tov_rate': 'Opp_Before_Game_Avg_TOV_Rate',
        'Opp_Before_Game_Avg_orb_pct': 'Opp_Before_Game_Avg_ORB_Pct'
    }

    renamed_count = 0
    for old_name, new_name in rename_map.items():
        if old_name in df.columns:
            df.rename(columns={old_name: new_name}, inplace=True)
            renamed_count += 1

    df.to_csv(output_file, index=False)
    print(f"成功修正 {renamed_count} 個欄位！已儲存至 '{output_file}'")

if __name__ == "__main__":
    run_fix_columns()