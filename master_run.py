import subprocess
import sys
import time
import os
import pandas as pd
import base64

def run_step(script_name):
    """執行外部 Python 腳本的函式"""
    print(f"\n" + "="*60)
    print(f" ▶ 正在執行: {script_name}")
    print("="*60)
    
    if not os.path.exists(script_name):
        print(f" [X] 錯誤：找不到檔案 '{script_name}'")
        return False

    start_time = time.time()
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        elapsed = time.time() - start_time
        print(f"\n [V] {script_name} 執行成功！ (耗時: {elapsed:.1f} 秒)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n [X] {script_name} 執行失敗！ (錯誤碼: {e.returncode})")
        return False
    except Exception as e:
        print(f"\n [X] 發生未預期錯誤: {e}")
        return False

def get_image_base64(image_path):
    """將圖片轉換為 Base64 字串以便嵌入 HTML"""
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def save_html_report():
    """
    生成包含圖表與多份報告的現代化儀表板 (index.html)
    """
    print("\n" + "="*60)
    print(" 🌐 正在生成現代化網頁報告 (index.html)...")
    print("="*60)

    # --- 1. 讀取 v800 報告 (原始邏輯) ---
    file_v800 = 'final_analysis_report_v800.csv'
    table_v800_html = ""
    if os.path.exists(file_v800):
        df8 = pd.read_csv(file_v800)
        if 'Home_Win_Prob' in df8.columns:
            df8['Home_Win_Prob'] = (df8['Home_Win_Prob'] * 100).fillna(0).astype(int).astype(str) + '%'
        for col in ['Diff_NetRtg', 'EV_Home', 'EV_Away']:
            if col in df8.columns: df8[col] = df8[col].round(2)
        table_v800_html = df8.to_html(classes='table table-hover align-middle', index=False, table_id='tableV800', border=0)

    # --- 2. 讀取 標準版 報告 (已修改為讀取 graded 檔案並篩選欄位) ---
    # 修改目標：換成 final_analysis_report_v800_graded.csv 並只留特定欄位
    file_std = 'final_analysis_report_v800_graded.csv'  # <--- 修改檔案來源
    table_std_html = ""
    
    # 指定要保留的欄位
    target_columns = [
        'Date', 'Home', 'Away', 'Home_Win_Prob', 'Confidence', 
        'Odds_Home', 'Odds_Away', 'EV_Home', 'EV_Away', 'Bet_Signal', 
        'Home_Score', 'Away_Score', 'Winner', 'Outcome'
    ]

    if os.path.exists(file_std):
        df_std = pd.read_csv(file_std)
        
        # 篩選欄位 (只保留存在的欄位，避免報錯)
        existing_cols = [c for c in target_columns if c in df_std.columns]
        df_std = df_std[existing_cols]

        # 格式化數據
        if 'Home_Win_Prob' in df_std.columns:
            # 判斷是否已經是百分比字串，如果不是才轉換
            if pd.api.types.is_numeric_dtype(df_std['Home_Win_Prob']):
                df_std['Home_Win_Prob'] = (df_std['Home_Win_Prob'] * 100).fillna(0).astype(int).astype(str) + '%'
        
        for col in ['EV_Home', 'EV_Away']:
            if col in df_std.columns: df_std[col] = df_std[col].round(2)
            
        table_std_html = df_std.to_html(classes='table table-hover align-middle', index=False, table_id='tableStd', border=0)
    else:
        print(f" [!] 警告：找不到標準報表檔案 '{file_std}'")

    # --- 3. 讀取圖片 ---
    img_accuracy = get_image_base64('accuracy_chart.png')
    img_html = ""
    if img_accuracy:
        img_html = f'<img src="data:image/png;base64,{img_accuracy}" class="img-fluid shadow rounded" alt="Accuracy Chart">'
    else:
        img_html = '<div class="alert alert-warning">尚未生成準確率圖表 (請確認 plot_accuracy.py 是否執行成功)</div>'

    # --- 4. 生成 HTML ---
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-Hant">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NBA AI 投資戰情室 (v3.0)</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
        <style>
            body {{ background-color: #f4f7f6; font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
            .navbar {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); box-shadow: 0 2px 10px rgba(0,0,0,0.2); }}
            .navbar-brand {{ color: white !important; font-weight: bold; letter-spacing: 1px; }}
            .content-box {{ background: white; border-radius: 12px; padding: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 30px; }}
            .nav-tabs .nav-link {{ color: #495057; font-weight: 600; }}
            .nav-tabs .nav-link.active {{ color: #1e3c72; border-top: 3px solid #1e3c72; }}
            
            /* 標籤樣式 */
            .badge-bet-home {{ background-color: #2ecc71; color: white; padding: 8px 12px; border-radius: 50px; font-weight: 600; display: inline-block; }}
            .badge-bet-away {{ background-color: #3498db; color: white; padding: 8px 12px; border-radius: 50px; font-weight: 600; display: inline-block; }}
            .prob-high {{ color: #2ecc71; font-weight: bold; font-size: 1.1em; }}
            .prob-low {{ color: #e74c3c; font-weight: bold; font-size: 1.1em; }}
        </style>
    </head>
    <body>

    <nav class="navbar navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="#"><i class="fas fa-basketball-ball me-2"></i>NBA AI 投資戰情室</a>
            <span class="text-white-50">Updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}</span>
        </div>
    </nav>

    <div class="container">
        
        <ul class="nav nav-tabs mb-4" id="myTab" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="v800-tab" data-bs-toggle="tab" data-bs-target="#v800" type="button">🚀 v800 策略推薦</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="std-tab" data-bs-toggle="tab" data-bs-target="#std" type="button">📊 標準版報表 (Graded)</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="chart-tab" data-bs-toggle="tab" data-bs-target="#chart" type="button">📈 模型準確率</button>
            </li>
        </ul>

        <div class="tab-content" id="myTabContent">
            
            <div class="tab-pane fade show active" id="v800" role="tabpanel">
                <div class="content-box">
                    <h4 class="mb-3 text-primary"><i class="fas fa-robot me-2"></i>v800 策略分析結果</h4>
                    <div class="table-responsive">
                        {table_v800_html if table_v800_html else '<p class="text-muted">無數據</p>'}
                    </div>
                </div>
            </div>

            <div class="tab-pane fade" id="std" role="tabpanel">
                <div class="content-box">
                    <h4 class="mb-3 text-secondary"><i class="fas fa-table me-2"></i>完整分析報表 (含回測結果)</h4>
                    <div class="table-responsive">
                        {table_std_html if table_std_html else '<p class="text-muted">無數據</p>'}
                    </div>
                </div>
            </div>

            <div class="tab-pane fade" id="chart" role="tabpanel">
                <div class="content-box text-center">
                    <h4 class="mb-4 text-info"><i class="fas fa-chart-line me-2"></i>模型準確率回測 (2026 賽季)</h4>
                    {img_html}
                    <p class="mt-3 text-muted">此圖表顯示模型在 2026 賽季的每日準確率 (藍線) 與累積準確率 (紅線) 變化。</p>
                </div>
            </div>
            
        </div>

        <footer class="text-center mt-5 mb-4 text-muted"><small>Powered by Python & GitHub Actions</small></footer>
    </div>

    <script src="https://code.jquery.com/jquery-3.5.1.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    
    <script>
        $(document).ready(function () {{
            // 設定 DataTables 共用函式
            function initTable(id) {{
                $(id).DataTable({{
                    "order": [[ 0, "desc" ]],
                    "pageLength": 25,
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/zh-Hant.json" }},
                    "createdRow": function( row, data, dataIndex ) {{
                        // 嘗試尋找 Bet_Signal 欄位並上色 (假設在倒數幾欄，這裡改用遍歷尋找較穩妥，或維持原邏輯)
                        // 因為欄位變動，這裡簡單做一個文字內容檢測
                        $('td', row).each(function() {{
                            var txt = $(this).text();
                            if (txt.includes('BET') || txt.includes('HOME') && txt.length < 20) {{ 
                                // length < 20 是為了避免誤判長字串
                                if (!txt.includes('Score') && !txt.includes('Prob')) {{
                                    $(this).html('<span class="badge-bet-home">' + txt + '</span>');
                                }}
                            }} else if (txt.includes('AWAY') && txt.length < 20) {{
                                $(this).html('<span class="badge-bet-away">' + txt + '</span>');
                            }}
                        }});
                        
                        // 勝率高亮
                        $('td', row).each(function(i) {{
                            var txt = $(this).text();
                            if (txt.includes('%')) {{
                                var val = parseInt(txt);
                                if (val >= 65) $(this).addClass('prob-high');
                                if (val <= 35) $(this).addClass('prob-low');
                            }}
                        }});
                    }}
                }});
            }}

            initTable('#tableV800');
            initTable('#tableStd');
        }});
    </script>
    </body>
    </html>
    """

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(" [V] 現代化 index.html 生成成功！")

def main():
    print("\n" + "#"*60)
    print(" 🏀 NBA 全自動投資系統 (Master Controller v3)")
    print("#"*60)
    
    pipeline = [
        # --- 階段 1: 數據更新 ---
        "v300_get_links.py",
        "v300_parse_data_incremental.py",
        "v400_get_current_injuries.py",
        
        # --- 階段 2: 特徵工程 ---
        "v200_gmsc_cumulative.py",
        "v1_update_v53.py",
        "v200data_process9.py",
        
        # --- 階段 3: 數據整合 ---
        "v200_merge_final.py",
        "fix_columns.py",
        
        # --- 階段 4: 回測與繪圖 (新增) ---
        "predictions_2026_full_report.py",
        "plot_accuracy.py",

        # --- 階段 5: 預測與分析 ---
        "v500_export_predictions.py",
        "v501_get_odds_for_prediction.py",
        "v600_merge_analysis.py",
        "v800_value_analyzer.py",
        
        # --- 階段 6: 成績結算 ---
        "v700_grade_report.py"
    ]

    total_steps = len(pipeline)
    for i, script in enumerate(pipeline):
        print(f"\n [進度] 步驟 {i+1}/{total_steps}...")
        if not run_step(script):
            print(f"警告：'{script}' 執行失敗或找不到，將嘗試繼續執行下一步...")
            continue

    print("\n" + "#"*60)
    print(" 🎉 恭喜！所有步驟執行完畢。")
    
    # --- 生成網頁 ---
    save_html_report()
    print("#"*60)

if __name__ == "__main__":
    main()
