import subprocess
import sys
import time
import os
import pandas as pd

def run_script(script_name):
    """執行一個 Python 子腳本，並檢查是否成功"""
    print(f"\n" + "="*60)
    print(f" >>> 正在啟動: {script_name} ...")
    print("="*60)
    
    start_time = time.time()
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        elapsed = time.time() - start_time
        print(f"\n[V] {script_name} 執行成功！ (耗時: {elapsed:.1f} 秒)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[X] {script_name} 執行失敗！ (錯誤碼: {e.returncode})")
        return False
    except Exception as e:
        print(f"\n[X] 發生未預期錯誤: {e}")
        return False

def main():
    print("\n" + "#"*60)
    print("     NBA 數據一鍵更新系統 (v302 終極版)")
    print("     目標：一次抓取球隊+球員 -> 計算特徵 -> 就緒")
    print("#"*60 + "\n")
    
    # ------------------------------------------------------
    # 階段 1: 增量爬蟲 (One-Stop Shop)
    # ------------------------------------------------------
    print("--- 階段 1: 增量爬蟲 ---")
    
    # 1. 抓取新連結
    # 讀取 nba_game_data_raw_v52_PATCHED.csv 檢查日期
    # 輸出: new_links_v300.csv
    if not run_script("v300_get_links.py"): return

    # 檢查是否有新連結
    skip_crawling = False
    if os.path.exists("new_links_v300.csv"):
        try:
            df_links = pd.read_csv("new_links_v300.csv")
            if df_links.empty:
                print("\n[!] 提示：沒有發現新的比賽連結。")
                skip_crawling = True
            else:
                print(f"\n[!] 發現 {len(df_links)} 場新比賽，開始同步抓取球隊與球員數據...")
        except:
            skip_crawling = False
    else:
        skip_crawling = True

    if not skip_crawling:
        # 2. 抓取並追加所有數據 (v300 Ultimate)
        # 輸入: new_links_v300.csv
        # 輸出 1: 追加到 nba_game_data_raw_v52_PATCHED.csv (球隊)
        # 輸出 2: 追加到 nba_player_single_game_gmsc_v52.csv (球員)
        # 包含 DNP 處理
        if not run_script("v300_parse_data_incremental.py"): return

    # ------------------------------------------------------
    # 階段 2: 特徵計算 (Feature Engineering)
    # ------------------------------------------------------
    print("\n--- 階段 2: 重新計算特徵 ---")
    
    # 3. 計算球員累積 GmSc (v108 part 1)
    # 輸入: nba_player_single_game_gmsc_v52.csv 
    # 輸出: nba_player_cumulative_gmsc_v108.csv
    # (檔名確認：v200_gmsc_cumulative.py)
    if not run_script("v200_gmsc_cumulative.py"): return 
    
    # 4. 計算球隊進階數據 (NetRtg - v53)
    # 輸入: nba_game_data_raw_v52_PATCHED.csv 
    # 輸出: v1_adv_stats_v53.csv
    if not run_script("v1_update_v53.py"): return
    
    # 5. 計算最終特徵 & 傷病指標 (v108 part 2)
    # 輸入: v52_PATCHED + v108_cumulative 
    # 輸出: FINAL_MASTER_v108_base.csv
    # (檔名確認：v200data_process9.py)
    if not run_script("v200data_process9.py"): return

    # ------------------------------------------------------
    # 階段 3: 最終整合 (Final Merge)
    # ------------------------------------------------------
    print("\n--- 階段 3: 最終整合 ---")
    
    # 6. 合併所有特徵 (v109)
    # 輸入: v108_base + v53_adv 
    # 輸出: FINAL_MASTER_DATASET_v109.csv
    # (檔名確認：v200_merge_final.py)
    if not run_script("v200_merge_final.py"): return
    
    # 7. 修正欄位名稱 (v109_FIXED)
    # 輸入: v109 
    # 輸出: FINAL_MASTER_DATASET_v109_FIXED.csv
    if not run_script("fix_columns.py"): return

    print("\n" + "#"*60)
    print(" 恭喜！所有數據已更新完畢。")
    print(" 您的最終模型數據庫: FINAL_MASTER_DATASET_v109_FIXED.csv")
    print(" 您現在可以執行預測腳本了。")
    print("#"*60)

if __name__ == "__main__":
    main()