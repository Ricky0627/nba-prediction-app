import subprocess
import sys
import time
import os

def run_step(script_name):
    """
    執行外部 Python 腳本的函式
    """
    print(f"\n" + "="*60)
    print(f" ▶ 正在執行: {script_name}")
    print("="*60)
    
    # 檢查檔案是否存在
    if not os.path.exists(script_name):
        print(f" [X] 錯誤：找不到檔案 '{script_name}'")
        print("     請確認該檔案是否在同一個資料夾中。")
        return False

    start_time = time.time()
    try:
        # 呼叫系統的 python 來執行該腳本
        result = subprocess.run([sys.executable, script_name], check=True)
        
        elapsed = time.time() - start_time
        print(f"\n [V] {script_name} 執行成功！ (耗時: {elapsed:.1f} 秒)")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n [X] {script_name} 執行失敗！ (錯誤碼: {e.returncode})")
        print("     請檢查上方的錯誤訊息。流程已中止。")
        return False
    except Exception as e:
        print(f"\n [X] 發生未預期錯誤: {e}")
        return False

def main():
    print("\n" + "#"*60)
    print(" 🏀 NBA 全自動投資系統 (Master Controller v2)")
    print(" 🎯 任務：更新數據 -> 預測 -> 賠率 -> 價值分析 -> 成績結算")
    print("#"*60)
    
    # ==========================================
    # 定義執行清單 (Pipeline)
    # ==========================================
    
    pipeline = [
        # --- 階段 1: 數據更新 (Data Update) ---
        "v300_get_links.py",               # 1. 找新比賽連結
        "v300_parse_data_incremental.py",  # 2. 抓比賽數據 (含 DNP)
        # "v202_patch_dnp.py",             # 3. DNP 雙重保險 (v300已內建，可選)
        "v400_get_current_injuries.py",    # 4. 抓即時傷病 (為了預測明天)
        
        # --- 階段 2: 特徵工程 (Feature Engineering) ---
        "v200_gmsc_cumulative.py",         # 5. 計算球員累積數據 (v108 part 1)
        "v1_update_v53.py",                # 6. 計算球隊進階數據 (NetRtg)
        "v200data_process9.py",            # 7. 計算最終特徵與傷病指標 (v108 part 2)
        
        # --- 階段 3: 數據整合 (Final Merge) ---
        "v200_merge_final.py",             # 8. 合併特徵 (v109)
        "fix_columns.py",                  # 9. 修正欄位名稱 (v109_FIXED)
        
        # --- 階段 4: 預測與分析 (Prediction & Analysis) ---
        "v500_export_predictions.py",      # 10. 預測明日比賽 (產出 predictions_xxx.csv)
        "v501_get_odds_for_prediction.py", # 11. 抓取對應賠率 (產出 odds_for_xxx.csv)
        
        "v600_merge_analysis.py",          # 12. 價值分析 (標準版) -> 產出 final_analysis_report.csv
        "v800_value_analyzer.py",          # 13. 價值分析 (策略優化版) -> 產出 final_analysis_report_v800.csv
        
        # --- 階段 5: 成績結算 (Grading) ---
        "v700_grade_report.py"             # 14. 自動對帳 (結算 v600 和 v800 的成績)
    ]

    # ==========================================
    # 開始依序執行
    # ==========================================
    total_steps = len(pipeline)
    
    for i, script in enumerate(pipeline):
        print(f"\n [進度] 步驟 {i+1}/{total_steps}...")
        
        # 某些步驟如果是可選的，可以在這裡加判斷
        # 但目前我們先全部執行
        success = run_step(script)
        
        if not success:
            print("\n" + "!"*60)
            print(f" 系統在執行 '{script}' 時發生錯誤，流程已停止。")
            print("!"*60)
            break
    else:
        # 如果迴圈正常結束 (沒有 break)
        print("\n" + "#"*60)
        print(" 🎉 恭喜！所有步驟執行完畢。")
        print(" 📊 請查看:")
        print("    1. final_analysis_report_graded.csv (標準版成績)")
        print("    2. final_analysis_report_v800_graded.csv (策略版成績)")
        print("#"*60)

if __name__ == "__main__":
    main()