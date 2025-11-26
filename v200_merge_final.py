import pandas as pd
import os

def merge_final_v200():
    """
    【v200 (第 8 步)：最終合併】
    將 'FINAL_MASTER_v108_base.csv' (基礎+傷病) 
    與 'v1_adv_stats_v53.csv' (NetRtg, Pace) 合併
    並產生 'FINAL_MASTER_DATASET_v109.csv'
    """
    print("--- 開始執行 v200 (第 8 步)：最終合併 (v109) ---")

    # 1. 定義檔案
    base_file = "FINAL_MASTER_v108_base.csv"
    adv_file = "v1_adv_stats_v53.csv"
    output_file = "FINAL_MASTER_DATASET_v109.csv"
    
    # 2. 檢查檔案
    if not os.path.exists(base_file) or not os.path.exists(adv_file):
        print("錯誤: 找不到 v108 或 v53 檔案。")
        print("請確保 'data_process9.py' 和 'v1_update_v53.py' 已執行成功。")
        return

    # 3. 讀取檔案
    print(f"正在讀取 '{base_file}'...")
    df_base = pd.read_csv(base_file)
    print(f"正在讀取 '{adv_file}'...")
    df_adv = pd.read_csv(adv_file)
    
    print(f"基礎數據筆數: {len(df_base)}")
    print(f"進階數據筆數: {len(df_adv)}")

    # --- 4. 清理數據 ---
    # 清理 v108 可能存在的重複欄位
    if 'Opp_Abbr.1' in df_base.columns:
        df_base = df_base.drop(columns=['Opp_Abbr.1'])

    # --- 5. 準備 v53 進階數據 (拆分主客隊) ---
    # v53 是「每隊每場」的格式，我們需要將其轉為「每場對戰」格式 (主 vs 客)
    
    # 我們只需要 'Before_Game_Avg_' 開頭的欄位 (NetRtg, Pace, etc.)
    adv_cols = [col for col in df_adv.columns if col.startswith('Before_Game_Avg_')]
    cols_to_keep = ['game_id', 'team'] + adv_cols

    # 5a. 準備主隊數據
    df_adv_home = df_adv[df_adv['location'] == 'Home'][cols_to_keep].copy()
    
    # 5b. 準備客隊數據
    df_adv_away = df_adv[df_adv['location'] == 'Away'][cols_to_keep].copy()
    
    # 客隊數據需要改名 (加上 Opp_ 前綴) 以便區分
    rename_dict = {col: f"Opp_{col}" for col in adv_cols}
    rename_dict['team'] = 'Opp_Abbr' 
    df_adv_away = df_adv_away.rename(columns=rename_dict)

    # --- 6. 執行合併 ---
    print("正在合併數據...")
    
    # 6a. 將主隊進階數據合併到主檔 (使用 game_id)
    # df_base 已經有 Team_Abbr，我們這裡不需要再從 df_adv_home 引入 'team'
    df_merged = pd.merge(
        df_base,
        df_adv_home.drop(columns=['team']), 
        on='game_id',
        how='inner'
    )

    # 6b. 將客隊進階數據合併到主檔
    df_final = pd.merge(
        df_merged,
        df_adv_away.drop(columns=['Opp_Abbr']), 
        on='game_id',
        how='inner'
    )

    # --- 7. 計算 Diff 特徵 (進階數據) ---
    # 我們需要算出 主隊 - 客隊 的差值
    print("正在計算進階數據的 Diff 特徵...")
    
    for col in adv_cols:
        home_col = col            # 例如: Before_Game_Avg_net_rtg
        opp_col = f"Opp_{col}"    # 例如: Opp_Before_Game_Avg_net_rtg
        diff_col = f"Diff_{col}"  # 例如: Diff_Before_Game_Avg_net_rtg
        
        if home_col in df_final.columns and opp_col in df_final.columns:
            df_final[diff_col] = df_final[home_col] - df_final[opp_col]

    # --- 8. 儲存 ---
    df_final.to_csv(output_file, index=False)
    
    print(f"\n--- 合併完成 ---")
    print(f"成功產生: {output_file} (共 {len(df_final)} 筆)")
    print("下一步：請執行 'fix_columns.py' 來修正欄位名稱大小寫。")

if __name__ == "__main__":
    merge_final_v200()