import subprocess
import sys
import time
import os
import pandas as pd  # <--- 新增這個，用於生成網頁

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

def save_html_report():
    """
    將分析結果轉換為 HTML 網頁 (index.html)
    """
    print("\n" + "="*60)
    print(" 🌐 正在生成網頁報告 (index.html)...")
    print("="*60)

    # 設定要讀取的檔案 (優先讀取 v800 策略版)
    # 如果你想顯示有結算成績的版本，可以改成 'final_analysis_report_v800_graded.csv'
    target_file = 'final_analysis_report_v800.csv'

    if not os.path.exists(target_file):
        print(f" [!] 找不到 {target_file}，跳過網頁生成。")
        return

    try:
        df = pd.read_csv(target_file)
        
        # 數據美化：將小數點格式化
        if 'Home_Win_Prob' in df.columns:
            df['Home_Win_Prob'] = df['Home_Win_Prob'].map('{:.2f}'.format)
        
        # 產生 HTML 表格
        table_html = df.to_html(classes='table table-striped table-hover', index=False, table_id='predictionTable')

        # 完整的 HTML 模板 (包含 Bootstrap 和 DataTables)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NBA AI 投資戰報</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
            <style>
                body {{ padding: 20px; background-color: #f8f9fa; font-family: "Microsoft JhengHei", sans-serif; }}
                .container {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 15px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; margin-bottom: 20px; text-align: center; font-weight: bold; }}
                .badge-custom {{ font-size: 0.9em; padding: 8px 12px; }}
            </style>
        </head>
        <body>
        <div class="container container-fluid">
            <h1>🏀 NBA AI 每日預測報告</h1>
            <div class="alert alert-info text-center">
                最後更新時間: <strong>{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
            </div>
            <div class="table-responsive">
                {table_html}
            </div>
        </div>
        <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        <script>
            $(document).ready(function () {{
                $('#predictionTable').DataTable({{
                    "order": [[ 0, "desc" ]],
                    "pageLength": 25,
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/zh-Hant.json" }}
                }});
            }});
        </script>
        </body>
        </html>
        """

        # 寫入檔案
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(" [V] index.html 生成成功！")

    except Exception as e:
        print(f" [X] 生成網頁時發生錯誤: {e}")

def main():
    print("\n" + "#"*60)
    print(" 🏀 NBA 全自動投資系統 (Master Controller v2)")
    print(" 🎯 任務：更新數據 -> 預測 -> 賠率 -> 價值分析 -> 成績結算 -> 網頁發布")
    print("#"*60)
    
    # ==========================================
    # 定義執行清單 (Pipeline)
    # ==========================================
    
    pipeline = [
        # --- 階段 1: 數據更新 (Data Update) ---
        "v300_get_links.py",               # 1. 找新比賽連結
        "v300_parse_data_incremental.py",  # 2. 抓比賽數據 (含 DNP)
        "v400_get_current_injuries.py",    # 4. 抓即時傷病 (為了預測明天)
        
        # --- 階段 2: 特徵工程 (Feature Engineering) ---
        "v200_gmsc_cumulative.py",         # 5. 計算球員累積數據
        "v1_update_v53.py",                # 6. 計算球隊進階數據 (NetRtg)
        "v200data_process9.py",            # 7. 計算最終特徵與傷病指標
        
        # --- 階段 3: 數據整合 (Final Merge) ---
        "v200_merge_final.py",             # 8. 合併特徵
        "fix_columns.py",                  # 9. 修正欄位名稱
        
        # --- 階段 4: 預測與分析 (Prediction & Analysis) ---
        "v500_export_predictions.py",      # 10. 預測明日比賽
        "v501_get_odds_for_prediction.py", # 11. 抓取對應賠率
        
        "v600_merge_analysis.py",          # 12. 價值分析 (標準版)
        "v800_value_analyzer.py",          # 13. 價值分析 (策略優化版)
        
        # --- 階段 5: 成績結算 (Grading) ---
        "v700_grade_report.py"             # 14. 自動對帳
    ]

    # ==========================================
    # 開始依序執行
    # ==========================================
    total_steps = len(pipeline)
    
    for i, script in enumerate(pipeline):
        print(f"\n [進度] 步驟 {i+1}/{total_steps}...")
        
        success = run_step(script)
        
        if not success:
            print("\n" + "!"*60)
            print(f" 系統在執行 '{script}' 時發生錯誤，流程已停止。")
            print("!"*60)
            break
    else:
        # 如果迴圈正常結束 (沒有 break)
        print("\n" + "#"*60)
        print(" 🎉 恭喜！所有分析步驟執行完畢。")
        print(" 📊 正在生成網頁報告...")
        
        # --- 執行網頁生成 ---
        save_html_report()
        
        print("#"*60)

if __name__ == "__main__":
    main()