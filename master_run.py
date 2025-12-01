import subprocess
import sys
import time
import os
import pandas as pd
import base64
import numpy as np

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

    # --- 1. 讀取 v800 報告 ---
    # 優先讀取結算後的檔案 (_graded)，如果沒有才讀原始檔
    file_v800 = 'final_analysis_report_v800_graded.csv'
    if not os.path.exists(file_v800):
        file_v800 = 'final_analysis_report_v800.csv'

    table_v800_html = ""
    if os.path.exists(file_v800):
        df8 = pd.read_csv(file_v800)
        if 'Home_Win_Prob' in df8.columns:
            if pd.api.types.is_numeric_dtype(df8['Home_Win_Prob']):
                df8['Home_Win_Prob'] = (df8['Home_Win_Prob'] * 100).fillna(0).astype(int).astype(str) + '%'
        for col in ['Diff_NetRtg', 'EV_Home', 'EV_Away']:
            if col in df8.columns: df8[col] = df8[col].round(2)
            
        # 處理比分顯示
        for col in ['Home_Score', 'Away_Score']:
            if col in df8.columns:
                df8[col] = df8[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else "-")
                
        table_v800_html = df8.to_html(classes='table table-hover align-middle', index=False, table_id='tableV800', border=0)

    # --- 2. 讀取 標準版 報告 (已修正：讀取 graded 並篩選欄位) ---
    file_std = 'final_analysis_report_graded.csv'
    table_std_html = ""
    
    if os.path.exists(file_std):
        try:
            df_std = pd.read_csv(file_std)
            
            # 指定保留的欄位 (User Requested)
            target_cols = [
                'Date', 'Home', 'Away', 'Home_Win_Prob', 'Confidence', 
                'Odds_Home', 'Odds_Away', 'EV_Home', 'EV_Away', 
                'Bet_Signal', 'Home_Score', 'Away_Score', 'Winner', 'Outcome'
            ]
            
            # 只保留存在的欄位
            valid_cols = [c for c in target_cols if c in df_std.columns]
            df_std = df_std[valid_cols]

            # 格式化勝率
            if 'Home_Win_Prob' in df_std.columns:
                if pd.api.types.is_numeric_dtype(df_std['Home_Win_Prob']):
                    df_std['Home_Win_Prob'] = (df_std['Home_Win_Prob'] * 100).fillna(0).astype(int).astype(str) + '%'
            
            # 格式化小數
            for col in ['EV_Home', 'EV_Away']:
                if col in df_std.columns: df_std[col] = df_std[col].round(2)
                
            # 格式化比分 (去小數點)
            for col in ['Home_Score', 'Away_Score']:
                if col in df_std.columns:
                    df_std[col] = df_std[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else "-")

            table_std_html = df_std.to_html(classes='table table-hover align-middle', index=False, table_id='tableStd', border=0)
        except Exception as e:
            print(f" [!] 處理標準版報告時發生錯誤: {e}")
            table_std_html = f'<div class="alert alert-danger">無法讀取報告: {e}</div>'
    else:
        table_std_html = '<div class="alert alert-warning">找不到結算報告 (final_analysis_report_graded.csv)</div>'

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
            
            /* 結果樣式 */
            .outcome-win {{ color: #2ecc71; font-weight: bold; }}
            .outcome-loss {{ color: #e74c3c; font-weight: bold; }}
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
                <button class="nav-link" id="std-tab" data-bs-toggle="tab" data-bs-target="#std" type="button">📊 標準版報表</button>
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
                    <h4 class="mb-3 text-secondary"><i class="fas fa-table me-2"></i>完整分析報表 (標準版)</h4>
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
            function initTable(id) {{
                $(id).DataTable({{
                    "order": [[ 0, "desc" ]],
                    "pageLength": 25,
                    "language": {{ "url": "//cdn.datatables.net/plug-ins/1.13.4/i18n/zh-Hant.json" }},
                    "createdRow": function( row, data, dataIndex ) {{
                        
                        $('td', row).each(function(i) {{
                            var content = $(this).text();
                            var cell = $(this);
                            
                            // 1. 處理 Bet_Signal
                            if (content.includes('BET') || content.includes('HOME') || (content.includes('主') && content.includes('EV'))) {{
                                if (content.includes('主') || content.includes('HOME')) cell.html('<span class="badge-bet-home">' + content + '</span>');
                            }} 
                            else if (content.includes('AWAY') || (content.includes('客') && content.includes('EV'))) {{
                                if (content.includes('客') || content.includes('AWAY')) cell.html('<span class="badge-bet-away">' + content + '</span>');
                            }}
                            
                            // 2. 處理勝率 (xx%)
                            if (content.includes('%') && content.length < 6) {{
                                var val = parseInt(content.replace('%', ''));
                                if (!isNaN(val)) {{
                                    if (val >= 65) cell.addClass('prob-high');
                                    if (val <= 35) cell.addClass('prob-low');
                                }}
                            }}

                            // 3. 處理 Outcome (WIN/LOSS)
                            if (content.includes('WIN') || content.includes('✅')) {{
                                cell.addClass('outcome-win');
                            }} else if (content.includes('LOSS') || content.includes('❌')) {{
                                cell.addClass('outcome-loss');
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
    print(" 🏀 NBA 全自動投資系統 (Master Controller v3.1)")
    print(" 🎯 任務：更新數據 -> 預測 -> 賠率 -> 價值分析 -> 成績結算 -> 網頁發布")
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
        
        # --- 階段 4: 回測與繪圖 ---
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
        
        success = run_step(script)
        
        if not success:
            print("\n" + "!"*60)
            print(f" 系統在執行 '{script}' 時發生錯誤，流程已停止。")
            print("!"*60)
            break
    else:
        print("\n" + "#"*60)
        print(" 🎉 恭喜！所有分析步驟執行完畢。")
        print(" 📊 正在生成網頁報告...")
        
        save_html_report()
        
        print("#"*60)

if __name__ == "__main__":
    main()
