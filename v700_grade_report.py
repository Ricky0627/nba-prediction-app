import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
import re
import time
import warnings
import numpy as np

# 忽略 Pandas 的 SettingWithCopyWarning
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)

def get_scores_from_bbr(date_str):
    """
    從 BBR 抓取指定日期 (YYYY-MM-DD) 的比分
    返回字典: { (Home_Abbr, Away_Abbr): (Home_Score, Away_Score) }
    """
    try:
        dt = pd.to_datetime(date_str)
        url = f"https://www.basketball-reference.com/boxscores/?month={dt.month}&day={dt.day}&year={dt.year}"
        print(f"  正在查詢比分: {date_str} ...")
        
        headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print("    無法連線到 BBR。")
            return {}

        soup = BeautifulSoup(response.content, 'lxml')
        summaries = soup.find_all('div', class_='game_summary')
        
        scores_map = {}
        
        for summary in summaries:
            teams = summary.find_all('tr')
            if len(teams) < 2: continue
            
            def extract_info(row):
                link = row.find('a', href=True)
                if not link: return None, None
                match = re.search(r'/teams/(\w{3})/', link['href'])
                abbr = match.group(1) if match else None
                score_cell = row.find('td', class_='right')
                score = int(score_cell.text) if score_cell and score_cell.text.isdigit() else None
                return abbr, score

            # 解析 Box Score 連結來確認主隊
            links = summary.find_all('a', href=True)
            box_link = None
            for l in links:
                if "boxscores" in l['href'] and ".html" in l['href']:
                    box_link = l['href']
                    break
            
            if box_link:
                match_home = re.search(r'0(\w{3})\.html', box_link)
                if match_home:
                    home_abbr_from_url = match_home.group(1)
                    team1_abbr, team1_score = extract_info(teams[0])
                    team2_abbr, team2_score = extract_info(teams[1])
                    
                    if not team1_abbr or not team2_abbr: continue
                    
                    if team1_abbr == home_abbr_from_url:
                        h_abbr, h_score = team1_abbr, team1_score
                        a_abbr, a_score = team2_abbr, team2_score
                    else:
                        h_abbr, h_score = team2_abbr, team2_score
                        a_abbr, a_score = team1_abbr, team1_score
                        
                    if h_score is not None and a_score is not None:
                        scores_map[(h_abbr, a_abbr)] = (h_score, a_score)
        
        return scores_map

    except Exception as e:
        print(f"    抓取失敗: {e}")
        return {}

def process_report(input_file, output_file, version_name):
    print(f"\n--- 正在處理報表: {version_name} ({input_file}) ---")
    
    if not os.path.exists(input_file):
        print(f"跳過: 找不到檔案 '{input_file}'")
        return

    df = pd.read_csv(input_file)
    
    # 確保欄位存在
    if 'Home_Score' not in df.columns: df['Home_Score'] = np.nan
    if 'Away_Score' not in df.columns: df['Away_Score'] = np.nan
    if 'Winner' not in df.columns: df['Winner'] = ""
    if 'Outcome' not in df.columns: df['Outcome'] = "" 

    unique_dates = df['Date'].unique()
    
    for date_str in unique_dates:
        # 篩選當日且尚未結算的比賽
        # 注意：如果 Outcome 已經有值但不是 "-"，我們就跳過
        # 但為了支援重新結算 (例如比分修正)，我們只檢查有沒有分數
        day_records = df[(df['Date'] == date_str)]
        
        # 檢查是否所有比賽都有結果了
        if day_records['Outcome'].isin(["✅ WIN", "❌ LOSS"]).all():
            continue 

        scores = get_scores_from_bbr(date_str)
        if not scores: continue
            
        for idx, row in day_records.iterrows():
            # 如果已經結算過，跳過 (避免重複 print)
            if row['Outcome'] in ["✅ WIN", "❌ LOSS"]: continue

            home = row['Home'] if 'Home' in row else row.get('Team_Abbr')
            away = row['Away'] if 'Away' in row else row.get('Opp_Abbr')
            
            result = scores.get((home, away))
            
            if result:
                h_score, a_score = result
                df.at[idx, 'Home_Score'] = h_score
                df.at[idx, 'Away_Score'] = a_score
                
                winner = home if h_score > a_score else away
                df.at[idx, 'Winner'] = winner
                
                # --- 核心邏輯：判定投資結果 ---
                signal = str(row['Bet_Signal']).upper()
                outcome = "-"
                
                # 支援 v600 ("主...EV") 和 v800 ("BET HOME...")
                bet_home = False
                bet_away = False
                
                if "主" in signal or "BET HOME" in signal:
                    bet_home = True
                elif "客" in signal or "BET AWAY" in signal:
                    bet_away = True
                
                # 排除 "觀望" 或 "PASS"
                if "觀望" in signal or "PASS" in signal or "無賠率" in signal:
                    bet_home = False
                    bet_away = False
                
                # 結算
                if bet_home:
                    if h_score > a_score: outcome = "✅ WIN"
                    else: outcome = "❌ LOSS"
                elif bet_away:
                    if a_score > h_score: outcome = "✅ WIN"
                    else: outcome = "❌ LOSS"
                    
                df.at[idx, 'Outcome'] = outcome
                
                if outcome != "-":
                    print(f"  [結算] {home} vs {away}: {h_score}-{a_score} | 訊號: {signal[:15]}... | 結果: {outcome}")
        
        time.sleep(1)

    # 計算統計
    graded = df[df['Outcome'].isin(["✅ WIN", "❌ LOSS"])]
    wins = len(graded[graded['Outcome'] == "✅ WIN"])
    losses = len(graded[graded['Outcome'] == "❌ LOSS"])
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
    
    # 計算 ROI (如果有的話)
    # 假設每注 1 單位
    # 獲利 = (賠率 - 1) * 1
    # 虧損 = -1
    net_profit = 0
    roi = 0
    
    # 嘗試計算 ROI
    try:
        for _, row in graded.iterrows():
            if row['Outcome'] == "✅ WIN":
                # 找出賠率
                odds = 0
                if "主" in str(row['Bet_Signal']) or "BET HOME" in str(row['Bet_Signal']):
                    odds = float(row['Odds_Home'])
                else:
                    odds = float(row['Odds_Away'])
                net_profit += (odds - 1)
            else:
                net_profit -= 1
        
        total_bet = wins + losses
        roi = (net_profit / total_bet) * 100 if total_bet > 0 else 0
    except:
        pass # 賠率欄位可能有問題，跳過 ROI 計算

    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"  -> [{version_name}] 總場次: {wins + losses} | 勝率: {win_rate:.1%} | 淨利: {net_profit:.2f}u | ROI: {roi:.1f}%")
    print(f"  -> 檔案更新: {output_file}")

def main():
    print("\n" + "="*60)
    print(" 📝 NBA 投資結算機器人 (v700 雙版本)")
    print("="*60)
    
    # 1. 處理 v600 (舊版)
    process_report("final_analysis_report.csv", "final_analysis_report_graded.csv", "v600 標準版")
    
    # 2. 處理 v800 (新版)
    process_report("final_analysis_report_v800.csv", "final_analysis_report_v800_graded.csv", "v800 策略版")

    print("\n" + "="*60)
    print(" 全部結算完畢。")

if __name__ == "__main__":
    main()