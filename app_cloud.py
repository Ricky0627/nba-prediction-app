import streamlit as st
import pandas as pd
import os
import subprocess
import sys
import time

# --- 設定 ---
st.set_page_config(page_title="NBA AI 雲端戰情室", page_icon="🏀", layout="wide")

# --- 標題 ---
st.title("🏀 NBA AI 全自動投資戰情室 (Cloud Ver.)")
st.caption("v800 模型 + v300 爬蟲 + v600 價值分析")

# --- 側邊欄 ---
with st.sidebar:
    st.header("控制台")
    if st.button("🔄 立即更新數據 & 預測", type="primary"):
        with st.status("正在執行雲端更新流程...", expanded=True) as status:
            st.write("啟動 master_run.py ...")
            
            # 執行 master_run.py
            # 注意：在雲端環境，我們必須確保所有路徑都正確
            try:
                process = subprocess.Popen(
                    [sys.executable, "master_run.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # 即時顯示日誌
                log_placeholder = st.empty()
                logs = ""
                for line in iter(process.stdout.readline, ''):
                    logs += line
                    # 只顯示最後 5 行日誌，避免刷屏
                    log_placeholder.code("\n".join(logs.splitlines()[-5:]))
                
                process.wait()
                
                if process.returncode == 0:
                    status.update(label="✅ 更新成功！", state="complete")
                    st.success("所有數據已更新至最新狀態。")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    status.update(label="❌ 更新失敗", state="error")
                    st.error("請檢查上方日誌。")
                    
            except Exception as e:
                st.error(f"執行錯誤: {e}")

# --- 主畫面：顯示報告 ---
tab1, tab2 = st.tabs(["📊 投資建議 (v800)", "📜 詳細歷史紀錄"])

def load_report(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return None

with tab1:
    df_v800 = load_report("final_analysis_report_v800.csv")
    if df_v800 is not None:
        latest_date = df_v800['Date'].max()
        st.subheader(f"📅 日期：{latest_date}")
        
        # 篩選當日
        df_today = df_v800[df_v800['Date'] == latest_date].copy()
        
        # 樣式設定
        def color_signal(val):
            if "BET" in str(val):
                return 'background-color: #d1e7dd; color: #0f5132; font-weight: bold;'
            return ''

        st.dataframe(
            df_today.style.applymap(color_signal, subset=['Bet_Signal']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("尚無 v800 報告，請點擊左側更新按鈕。")

with tab2:
    df_history = load_report("final_analysis_report_v800_graded.csv")
    if df_history is not None:
        st.dataframe(df_history, use_container_width=True)
    else:
        st.info("尚無結算後的歷史紀錄。")