import pandas as pd
import numpy as np
import os
import glob
import re

def find_latest_files():
    """自動尋找最新的預測檔和賠率檔"""
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
    hp = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)', 0.5))
    ap = 1.0 - hp
    
    try:
        ho = float(row.get('Odds_Home', np.nan))
    except: ho = np.nan
        
    try:
        ao = float(row.get('Odds_Away', np.nan))
    except: ao = np.nan
    
    if pd.notna(ho): ev_home = (hp * ho) - 1
    else: ev_home = np.nan
        
    if pd.notna(ao): ev_away = (ap * ao) - 1
    else: ev_away = np.nan
        
    return ev_home, ev_away

def get_v800_signal(row):
    """
    【v800.2 策略核心 - 基於 v850 校準報告優化】
    """
    hp = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)'))
    eh = row['EV_Home']
    ea = row['EV_Away']
    
    if pd.isna(eh) or pd.isna(ea): return "無賠率"

    signal = []
    
    # --- 策略 A: 主勝穩膽區 (0.7 - 0.9) ---
    # 校準報告: 實際勝率 ~80%，偏差極小。這是最穩的區間。
    if 0.70 <= hp < 0.90:
        if eh > 0:
            conf = "🔥" if eh > 0.1 else ""
            signal.append(f"BET HOME (Solid) EV={eh:.2f}{conf}")
        else:
            # 即使沒 EV，但勝率極高，可作為串關配腳
            signal.append(f"HOME (Parlay) Win={hp:.0%}")

    # --- 策略 B: 客勝狙擊區 (0.2 - 0.3) ---
    # 校準報告: 主勝率 ~17% (即客勝 ~83%)。模型在此區間表現優異。
    elif 0.20 <= hp < 0.30:
        if ea > 0:
            conf = "🔥" if ea > 0.1 else ""
            signal.append(f"BET AWAY (Sniper) EV={ea:.2f}{conf}")
        else:
            signal.append(f"AWAY (Parlay) Win={1-hp:.0%}")

    # --- 策略 C: 價值挖掘區 (0.5 - 0.6) ---
    # 校準報告: 模型預測 ~55%，實際 ~63%。模型低估了主隊。
    # 這裡我們給予主隊 EV 加權 (+8%) 再判斷
    elif 0.50 <= hp < 0.60:
        adjusted_hp = hp + 0.08 
        adjusted_ev_h = (adjusted_hp * float(row.get('Odds_Home', 0))) - 1
        
        if adjusted_ev_h > 0:
            star = "💎" # 鑽石標記：隱藏價值
            signal.append(f"BET HOME (Value) AdjEV={adjusted_ev_h:.2f}{star}")

    # --- 策略 D: 極端值警示 (0.1-0.2 & 0.9-1.0) ---
    # 校準報告: 模型在此過度自信，建議保守。
    elif hp >= 0.90:
        if eh > 0.05: # 要求更高的 EV 門檻
            signal.append(f"BET HOME (Lock) EV={eh:.2f}")
        else:
            signal.append(f"PASS (Too Low Odds)")
            
    elif hp < 0.20:
        if ea > 0.05:
            signal.append(f"BET AWAY (Lock) EV={ea:.2f}")
        else:
            signal.append(f"PASS (Too Low Odds)")

    # --- 其他區間 ---
    else:
        # 0.3-0.4, 0.4-0.5, 0.6-0.7: 模型準確，但勝負難料
        # 只投高 EV
        if eh > 0.15: signal.append(f"主EV高={eh:.2f} (Risky)")
        if ea > 0.15: signal.append(f"客EV高={ea:.2f} (Risky)")

    return " | ".join(signal) if signal else "觀望"

def main():
    print("\n" + "="*60)
    print(" 💰 NBA 價值分析器 (v800.2 - 校準優化版)")
    print(" 🎯 依據 v850 報告調整策略權重")
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
        
        # 產生訊號
        df_final['Bet_Signal'] = df_final.apply(get_v800_signal, axis=1)
        
        # 清理欄位
        cols_to_drop = ['Home_Abbr', 'Away_Abbr']
        df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns])
        
    else:
        df_final = df_pred
        df_final['Odds_Home'] = np.nan; df_final['Odds_Away'] = np.nan
        df_final['EV_Home'] = np.nan; df_final['EV_Away'] = np.nan
        df_final['Bet_Signal'] = "無賠率"

    # 儲存與顯示
    output_file = "final_analysis_report_v800.csv"
    
    # 追加邏輯 (與 v600 相同)
    if os.path.exists(output_file):
        try:
            df_history = pd.read_csv(output_file)
            home_col = 'Home' if 'Home' in df_final.columns else 'Team_Abbr'
            df_final['unique_key'] = df_final['Date'].astype(str) + "_" + df_final[home_col]
            
            if home_col in df_history.columns:
                df_history['unique_key'] = df_history['Date'].astype(str) + "_" + df_history[home_col]
                df_history = df_history[~df_history['unique_key'].isin(df_final['unique_key'])]
                df_combined = pd.concat([df_history, df_final], ignore_index=True)
                df_combined = df_combined.drop(columns=['unique_key'])
                df_combined = df_combined.sort_values(by='Date', ascending=False)
            else:
                df_combined = df_final
                if 'unique_key' in df_combined.columns: df_combined = df_combined.drop(columns=['unique_key'])
        except:
            df_combined = df_final
    else:
        df_combined = df_final

    # 顯示
    print("\n" + "-"*100)
    print(f"{'日期':<12} | {'對戰':<10} | {'主勝率':<6} | {'賠率':<10} | {'訊號 (v800.2)'}")
    print("-" * 100)
    
    for _, row in df_final.iterrows():
        if 'Home' in row: home, away = row['Home'], row['Away']
        else: home, away = row['Team_Abbr'], row['Opp_Abbr']
        
        prob = row.get('Home_Win_Prob', row.get('Predicted_Prob_Win (1)'))
        odds = f"{row['Odds_Home']}/{row['Odds_Away']}" if pd.notna(row['Odds_Home']) else "-/-"
        
        is_bet = "BET" in str(row['Bet_Signal'])
        prefix = ">> " if is_bet else "   "
        
        print(f"{prefix}{row['Date']:<12} | {home}v{away:<4} | {prob:.1%}    | {odds:<10} | {row['Bet_Signal']}")

    df_combined.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("\n" + "="*60)
    print(f" 策略分析完成！已儲存至: {output_file}")
    print("="*60)

if __name__ == "__main__":
    main()