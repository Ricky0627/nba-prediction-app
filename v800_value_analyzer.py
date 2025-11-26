import pandas as pd
import numpy as np
import os
import glob
import re

def find_latest_files():
    """
    自動尋找最新的預測檔，並嘗試找到對應的賠率檔
    """
    pred_files = glob.glob("predictions_*.csv")
    valid_preds = []
    pattern = re.compile(r"predictions_(\d{4}-\d{2}-\d{2})\.csv")
    
    for f in pred_files:
        if pattern.match(os.path.basename(f)):
            valid_preds.append(f)
            
    if not valid_preds: return None, None
        
    latest_pred = max(valid_preds, key=os.path.getctime)
    date_str = pattern.match(os.path.basename(latest_pred)).group(1)
    odds_file = f"odds_for_{date_str}.csv"
    
    if not os.path.exists(odds_file):
        print(f"警告: 找不到對應賠率檔 '{odds_file}' (將只顯示預測)")
        return latest_pred, None
        
    return latest_pred, odds_file

def calculate_ev(row):
    """計算 EV"""
    # 欄位名稱兼容
    hp = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)', 0.5))
    ap = 1.0 - hp
    
    # 處理賠率可能的空值或錯誤格式
    try:
        ho = float(row.get('Odds_Home', np.nan))
    except:
        ho = np.nan
        
    try:
        ao = float(row.get('Odds_Away', np.nan))
    except:
        ao = np.nan
    
    # 計算主隊 EV
    if pd.notna(ho):
        ev_home = (hp * ho) - 1
    else:
        ev_home = np.nan
        
    # 計算客隊 EV
    if pd.notna(ao):
        ev_away = (ap * ao) - 1
    else:
        ev_away = np.nan
        
    return ev_home, ev_away

def get_v800_signal(row):
    """
    v800 核心邏輯：基於校準度分析的策略調整
    """
    hp = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)'))
    eh = row['EV_Home']
    ea = row['EV_Away']
    
    if pd.isna(eh) or pd.isna(ea): return "無賠率"

    signal = []
    
    # --- 策略 1: 避開 80-90% 的過度自信陷阱 ---
    if 0.80 <= hp < 0.90:
        return "PASS (Overconf. Risk)" # 強制跳過

    # --- 策略 2: 鎖定甜蜜點 (70-80% 主勝) ---
    if 0.70 <= hp < 0.80 and eh > 0:
        conf = "🔥" if eh > 0.1 else ""
        signal.append(f"BET HOME (Strong) EV={eh:.2f}{conf}")

    # --- 策略 3: 鎖定客隊刺客 (20-30% 主勝 = 70-80% 客勝) ---
    if 0.20 <= hp < 0.30 and ea > 0:
        conf = "🔥" if ea > 0.1 else ""
        signal.append(f"BET AWAY (Sniper) EV={ea:.2f}{conf}")

    # --- 策略 4: 極端值穩膽 (<20% 或 >90%) ---
    if hp >= 0.90:
        signal.append(f"BET HOME (Lock) EV={eh:.2f}")
    if hp < 0.20:
        signal.append(f"BET AWAY (Lock) EV={ea:.2f}")

    # --- 策略 5: 忽略中間地帶 (40-60%) 的微弱優勢 ---
    # 如果 EV 非常高 (>0.15) 且不在上述區間，才勉強考慮，否則 PASS
    if not signal:
        if 0.40 <= hp < 0.60:
            return "PASS (Noise Zone)"
        if eh > 0.15: signal.append(f"主EV高={eh:.2f} (Risky)")
        if ea > 0.15: signal.append(f"客EV高={ea:.2f} (Risky)")

    return " | ".join(signal) if signal else "觀望"

def main():
    print("\n" + "="*60)
    print(" 💰 NBA 價值分析器 (v800 - 策略優化版)")
    print(" 🎯 目標：累積投資記錄 (Append Mode)")
    print(" 🛠️  修正：避開 80-90% 陷阱，鎖定 70-80% & 20-30% 區間")
    print("="*60)
    
    # 1. 載入檔案
    pred_file, odds_file = find_latest_files()
    if not pred_file:
        print("錯誤: 找不到預測檔案。")
        return

    print(f"讀取預測: {pred_file}")
    df_pred = pd.read_csv(pred_file)
    
    if odds_file:
        print(f"讀取賠率: {odds_file}")
        df_odds = pd.read_csv(odds_file)
        
        # 合併
        if 'Home' in df_pred.columns:
            left_on = ['Home', 'Away']
        else:
            left_on = ['Team_Abbr', 'Opp_Abbr']
            
        df_final = pd.merge(
            df_pred,
            df_odds[['Home_Abbr', 'Away_Abbr', 'Odds_Home', 'Odds_Away']],
            left_on=left_on,
            right_on=['Home_Abbr', 'Away_Abbr'],
            how='left'
        )
        
        # 計算 EV
        ev_results = df_final.apply(calculate_ev, axis=1, result_type='expand')
        df_final['EV_Home'] = ev_results[0]
        df_final['EV_Away'] = ev_results[1]
        
        # 產生訊號 (使用 v800 新邏輯)
        df_final['Bet_Signal'] = df_final.apply(get_v800_signal, axis=1)
        
        # 清理多餘欄位
        cols_to_drop = ['Home_Abbr', 'Away_Abbr'] 
        df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns])
        
    else:
        df_final = df_pred
        df_final['Odds_Home'] = np.nan
        df_final['Odds_Away'] = np.nan
        df_final['EV_Home'] = np.nan
        df_final['EV_Away'] = np.nan
        df_final['Bet_Signal'] = "無賠率"

    # --- 輸出檔名變更為 v800 ---
    output_file = "final_analysis_report_v800.csv"
    
    if os.path.exists(output_file):
        print(f"\n正在讀取現有報告 '{output_file}' 以便追加...")
        try:
            df_history = pd.read_csv(output_file)
            
            # 為了去重，我們需要一個唯一鍵
            home_col = 'Home' if 'Home' in df_final.columns else 'Team_Abbr'
            
            # 標記新數據的 Key
            df_final['unique_key'] = df_final['Date'].astype(str) + "_" + df_final[home_col]
            
            if home_col in df_history.columns:
                df_history['unique_key'] = df_history['Date'].astype(str) + "_" + df_history[home_col]
                
                # 移除舊數據中與新數據 Key 相同的行 (覆蓋舊數據)
                df_history = df_history[~df_history['unique_key'].isin(df_final['unique_key'])]
                
                # 合併
                df_combined = pd.concat([df_history, df_final], ignore_index=True)
                
                # 移除臨時 Key
                df_combined = df_combined.drop(columns=['unique_key'])
                
                # 重新排序 (按日期)
                df_combined = df_combined.sort_values(by='Date', ascending=False)
                
            else:
                print("警告：新舊檔案格式不符，將直接覆蓋。")
                df_combined = df_final
                if 'unique_key' in df_combined.columns: df_combined = df_combined.drop(columns=['unique_key'])

        except Exception as e:
            print(f"讀取舊檔失敗 ({e})，將建立新檔。")
            df_combined = df_final
            if 'unique_key' in df_combined.columns: df_combined = df_combined.drop(columns=['unique_key'])
    else:
        print(f"\n建立新報告 '{output_file}'...")
        df_combined = df_final
        if 'unique_key' in df_combined.columns: df_combined = df_combined.drop(columns=['unique_key'])

    # 5. 顯示與儲存
    print("\n" + "-"*100)
    print(f"{'日期':<12} | {'對戰':<10} | {'主勝率':<6} | {'賠率':<10} | {'訊號'}")
    print("-" * 100)
    
    # 只顯示最新的幾筆 (本次新增的)
    for _, row in df_final.iterrows():
        if 'Home' in row: home, away = row['Home'], row['Away']
        else: home, away = row['Team_Abbr'], row['Opp_Abbr']
        
        prob = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)'))
        odds = f"{row['Odds_Home']}/{row['Odds_Away']}" if pd.notna(row['Odds_Home']) else "-/-"
        
        # 標記高亮
        is_bet = "BET" in row['Bet_Signal']
        prefix = ">> " if is_bet else "   "
        
        print(f"{prefix}{row['Date']:<12} | {home}v{away:<4} | {prob:.1%}    | {odds:<10} | {row['Bet_Signal']}")

    # 存檔
    df_combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("\n" + "="*60)
    print(f" 已將 {len(df_final)} 筆新記錄追加至: {output_file}")
    print(f" 目前總記錄數: {len(df_combined)}")
    print("="*60)

if __name__ == "__main__":
    main()