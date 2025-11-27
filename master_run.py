import subprocess
import sys
import time
import os
import pandas as pd  # 確保 requirements.txt 有包含 pandas

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
    將分析結果轉換為現代化儀表板網頁 (index.html)
    """
    print("\n" + "="*60)
    print(" 🌐 正在生成現代化網頁報告 (index.html)...")
    print("="*60)

    # 設定要讀取的檔案 (優先讀取 v800 策略版)
    target_file = 'final_analysis_report_v800.csv'

    if not os.path.exists(target_file):
        print(f" [!] 找不到 {target_file}，跳過網頁生成。")
        return

    try:
        df = pd.read_csv(target_file)
        
        # --- 數據預處理 (為了儀表板卡片計算) ---
        total_games = len(df)
        
        # 計算有多少場是推薦下注的 (假設 Bet_Signal 包含 'BET' 字眼)
        bet_count = df[df['Bet_Signal'].astype(str).str.contains("BET", case=False, na=False)].shape[0]
        
        # 找出最大 EV 值
        max_ev = 0
        if 'EV_Home' in df.columns and 'EV_Away' in df.columns:
            max_home = df['EV_Home'].max()
            max_away = df['EV_Away'].max()
            max_ev = max(max_home, max_away)

        # 格式化顯示數據：將勝率轉為百分比字串 (例如 0.85 -> 85%)
        if 'Home_Win_Prob' in df.columns:
            df['Home_Win_Prob'] = (df['Home_Win_Prob'] * 100).fillna(0).astype(int).astype(str) + '%'

        # 小數點位數格式化 (EV, NetRtg 等)
        for col in ['Diff_NetRtg', 'EV_Home', 'EV_Away']:
            if col in df.columns:
                df[col] = df[col].round(2)
            
        # 產生 HTML 表格 (不帶樣式，樣式由 DataTables 控制)
        table_html = df.to_html(classes='table table-hover align-middle', index=False, table_id='predictionTable', border=0)

        # --- HTML 模板 (包含 CSS/JS) ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-Hant">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NBA AI 投資戰情室</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
            <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
            
            <style>
                :root {{
                    --primary-color: #1a252f;
                    --accent-color: #3498db;
                    --success-color: #2ecc71;
                    --warning-color: #f1c40f;
                    --danger-color: #e74c3c;
                    --bg-color: #f4f7f6;
                }}
                
                body {{ 
                    background-color: var(--bg-color); 
                    font-family: 'Segoe UI', "Microsoft JhengHei", sans-serif;
                    color: #333;
                }}

                /* 頂部導航 */
                .navbar {{
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }}
                .navbar-brand {{
                    color: white !important;
                    font-weight: bold;
                    letter-spacing: 1px;
                }}

                /* 儀表板卡片 */
                .stat-card {{
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                    transition: transform 0.2s;
                    border-left: 5px solid var(--accent-color);
                }}
                .stat-card:hover {{ transform: translateY(-3px); }}
                .stat-title {{ color: #7f8c8d; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }}
                .stat-value {{ font-size: 2rem; font-weight: bold; color: var(--primary-color); }}
                .stat-icon {{ font-size: 2.5rem; opacity: 0.2; position: absolute; right: 20px; top: 20px; }}

                /* 表格區域 */
                .table-container {{
                    background: white;
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                    margin-top: 30px;
                    border-top: 5px solid #2c3e50;
                }}
                
                table.dataTable thead th {{
                    background-color: #f8f9fa;
                    color: #2c3e50;
                    font-weight: 700;
                    border-bottom: 2px solid #dee2e6;
                }}

                /* 標籤樣式 */
                .badge-bet-home {{ background-color: var(--success-color); color: white; padding: 8px 12px; border-radius: 50px; box-shadow: 0 2px 5px rgba(46,204,113,0.4); }}
                .badge-bet-away {{ background-color: var(--accent-color); color: white; padding: 8px 12px; border-radius: 50px; }}
                .badge-watch {{ background-color: #95a5a6; color: white; padding: 5px 10px; border-radius: 4px; font-size: 0.85em; }}
                
                /* 強弱指標 */
                .prob-high {{ color: var(--success-color); font-weight: bold; }}
                .prob-low {{ color: var(--danger-color); }}
                
                /* 隊伍名稱加粗 */
                td:nth-child(2), td:nth-child(3) {{
                    font-weight: 600;
                    color: #2c3e50;
                }}
            </style>
        </head>
        <body>

        <nav class="navbar navbar-dark mb-4">
            <div class="container">
                <a class="navbar-brand" href="#">
                    <i class="fas fa-basketball-ball me-2"></i>NBA AI 投資戰情室
                </a>
                <span class="text-white-50" style="font-size: 0.9em;">
                    最後更新: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
                </span>
            </div>
        </nav>

        <div class="container">
            
            <div class="row g-4 mb-4">
                <div class="col-md-4">
                    <div class="stat-card" style="border-left-color: #3498db;">
                        <div class="stat-title">今日賽事</div>
                        <div class="stat-value">{total_games} <span style="font-size:1rem; color:#999;">場</span></div>
                        <i class="fas fa-calendar-day stat-icon text-primary"></i>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card" style="border-left-color: #2ecc71;">
                        <div class="stat-title">AI 推薦注單</div>
                        <div class="stat-value">{bet_count} <span style="font-size:1rem; color:#999;">單</span></div>
                        <i class="fas fa-check-circle stat-icon text-success"></i>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card" style="border-left-color: #f1c40f;">
                        <div class="stat-title">最高期望值 (EV)</div>
                        <div class="stat-value">+{max_ev:.2f}</div>
                        <i class="fas fa-chart-line stat-icon text-warning"></i>
                    </div>
                </div>
            </div>

            <div class="table-container">
                <h4 class="mb-4"><i class="fas fa-list me-2"></i>賽事分析詳情</h4>
                <div class="table-responsive">
                    {table_html}
                </div>
            </div>

            <footer class="text-center mt-5 mb-4 text-muted">
                <small>Designed by AI • Powered by GitHub Actions</small>
            </footer>
        </div>

        <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
        <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
        
        <script>
            $(document).ready(function () {{
                // 初始化 DataTables
                var table = $('#predictionTable').DataTable({{
                    "order": [[ 0, "desc" ]], // 預設依日期排序
                    "pageLength": 25,
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/zh-Hant.json" }},
                    
                    // --- 關鍵：這裡控制每一行的樣式 ---
                    "createdRow": function( row, data, dataIndex ) {{
                        // 1. 抓取 Bet_Signal (假設在最後一欄)
                        var lastColIndex = data.length - 1; 
                        var signal = data[lastColIndex];
                        var cell = $('td', row).eq(lastColIndex);

                        // 2. 根據內容加上標籤樣式
                        if (signal.includes('BET') || signal.includes('HOME')) {{
                            cell.html('<span class="badge-bet-home"><i class="fas fa-home me-1"></i>' + signal + '</span>');
                        }} else if (signal.includes('AWAY')) {{
                            cell.html('<span class="badge-bet-away"><i class="fas fa-plane me-1"></i>' + signal + '</span>');
                        }} else if (signal.includes('觀望') || signal.includes('PASS')) {{
                            cell.html('<span class="badge-watch">' + signal + '</span>');
                        }}

                        // 3. 處理勝率 (Home_Win_Prob) 假設在第 4 欄 (index 3)
                        var winProbCell = $('td', row).eq(3);
                        var winProbText = winProbCell.text();
                        var winProbVal = parseInt(winProbText.replace('%', ''));
                        
                        if (winProbVal >= 60) {{
                            winProbCell.addClass('prob-high');
                            winProbCell.html(winProbText + ' <i class="fas fa-fire text-danger" style="font-size:0.8em;"></i>');
                        }}
                    }}
                }});
            }});
        </script>
        </body>
        </html>
        """

        # 寫入檔案
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(" [V] 現代化 index.html 生成成功！")

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