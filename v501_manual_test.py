import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import os
import re

# --- 1. 隊名對照表 (完整版) ---
TEAM_MAP = {
    '老鷹': 'ATL', '塞爾提克': 'BOS', '塞爾提': 'BOS',
    '籃網': 'BRK', '黃蜂': 'CHO',
    '公牛': 'CHI', '騎士': 'CLE', '獨行俠': 'DAL', '金塊': 'DEN',
    '活塞': 'DET', '勇士': 'GSW', '火箭': 'HOU', '溜馬': 'IND',
    '快艇': 'LAC', '湖人': 'LAL', '灰熊': 'MEM', '熱火': 'MIA',
    '公鹿': 'MIL', '灰狼': 'MIN', '鵜鶘': 'NOP', '尼克': 'NYK',
    '雷霆': 'OKC', '魔術': 'ORL', '76人': 'PHI', '七六人': 'PHI',
    '太陽': 'PHO', '拓荒者': 'POR', '拓荒': 'POR',
    '國王': 'SAC', '馬刺': 'SAS', '暴龍': 'TOR',
    '爵士': 'UTA', '巫師': 'WAS'
}

def get_playsport_odds_robust(target_date_str):
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={target_date_str}"
    print(f"正在抓取 PlaySport 頁面: {target_date_str} ...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 1. 找到所有帶有 gameid 的行
        game_rows = soup.find_all('tr', attrs={'gameid': True})
        if not game_rows:
            print("錯誤: 找不到任何比賽行 (gameid)")
            return []
            
        print(f"找到 {len(game_rows)} 個原始行，開始分組解析...")

        # 2. 根據 gameid 分組
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue # 資料不完整
            
            # Row 0 = 客隊, Row 1 = 主隊
            r_away = rows[0]
            r_home = rows[1]
            
            # --- 解析隊名 ---
            def extract_team_name(row):
                td = row.find('td', class_='td-teaminfo')
                if not td: return None
                # 優先找連結
                links = td.find_all('a')
                for link in links:
                    txt = link.text.strip()
                    if txt in TEAM_MAP: return txt
                # 備用：找純文字 (有些隊名可能沒連結)
                # 但這比較危險，可能抓到 "對戰資訊"
                return None

            # 這裡有個陷阱：如果結構是 11/23 那樣 (兩隊名都在第一行)
            # r_away 裡面會有兩個連結，r_home 裡面可能沒有
            
            teams_in_away_row = []
            td_away = r_away.find('td', class_='td-teaminfo')
            if td_away:
                for link in td_away.find_all('a'):
                    txt = link.text.strip()
                    if txt in TEAM_MAP: teams_in_away_row.append(txt)
            
            if len(teams_in_away_row) >= 2:
                # Case A: 兩隊都在第一行 (如 11/23)
                away_name_ch = teams_in_away_row[0]
                home_name_ch = teams_in_away_row[1]
            else:
                # Case B: 分開在兩行 (如 11/24)
                away_name_ch = extract_team_name(r_away)
                home_name_ch = extract_team_name(r_home)
            
            if not away_name_ch or not home_name_ch:
                # print(f"  跳過: 無法識別隊名 (GID: {gid})")
                continue

            # --- 解析賠率 ---
            def extract_odd(row):
                if not row: return np.nan
                td = row.find('td', class_='td-bank-bet03')
                if not td: return np.nan
                txt = td.get_text().strip()
                import re
                nums = re.findall(r"[-+]?\d*\.\d+|\d+", txt)
                if nums: return float(nums[-1])
                return np.nan

            odd_away = extract_odd(r_away)
            odd_home = extract_odd(r_home)
            
            # 轉換
            away_abbr = TEAM_MAP.get(away_name_ch, "UNKNOWN")
            home_abbr = TEAM_MAP.get(home_name_ch, "UNKNOWN")
            
            print(f"  抓到: {away_name_ch}({away_abbr}) vs {home_name_ch}({home_abbr}) | 賠率: {odd_away} / {odd_home}")
            
            daily_data.append({
                'Date_TW': target_date_str,
                'Away_Abbr': away_abbr,
                'Home_Abbr': home_abbr,
                'Odds_Away': odd_away,
                'Odds_Home': odd_home
            })
            
        return daily_data

    except Exception as e:
        print(f"  抓取失敗: {e}")
        return []

def main():
    # 測試 11/24 (美國 11/23)
    target_date = "20251124"
    us_date = "2025-11-23"
    
    print(f"--- v501.4 (通用版) 測試: {target_date} ---")
    odds = get_playsport_odds_robust(target_date)
    
    if odds:
        df = pd.DataFrame(odds)
        file_name = f"odds_for_{us_date}.csv"
        df.to_csv(file_name, index=False, encoding='utf-8-sig')
        print(f"\n成功！已儲存至 {file_name}")
    else:
        print("無數據。")

if __name__ == "__main__":
    main()