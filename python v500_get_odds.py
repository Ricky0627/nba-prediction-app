import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import datetime
import os

# --- 1. 設定日期範圍 ---
# 2026 賽季大約從 2025-10-22 開始
START_DATE = "20251022"
END_DATE = "20251123" 
OUTPUT_FILE = "nba_odds_2026_v500.csv"

# --- 2. 隊名對照表 (玩運彩中文 -> BBR 縮寫) ---
# 這非常重要，用於後續合併
TEAM_MAP = {
    '老鷹': 'ATL', '塞爾提克': 'BOS', '籃網': 'BRK', '黃蜂': 'CHO',
    '公牛': 'CHI', '騎士': 'CLE', '獨行俠': 'DAL', '金塊': 'DEN',
    '活塞': 'DET', '勇士': 'GSW', '火箭': 'HOU', '溜馬': 'IND',
    '快艇': 'LAC', '湖人': 'LAL', '灰熊': 'MEM', '熱火': 'MIA',
    '公鹿': 'MIL', '灰狼': 'MIN', '鵜鶘': 'NOP', '尼克': 'NYK',
    '雷霆': 'OKC', '魔術': 'ORL', '76人': 'PHI', '太陽': 'PHO',
    '拓荒者': 'POR', '國王': 'SAC', '馬刺': 'SAS', '暴龍': 'TOR',
    '爵士': 'UTA', '巫師': 'WAS'
}

def get_odds_for_date(date_str, session):
    """
    抓取指定日期的玩運彩賠率
    """
    url = f"https://www.playsport.cc/gamesData/result?allianceid=3&gametime={date_str}"
    print(f"正在抓取 {date_str} 的賠率... ({url})")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = session.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"  錯誤: HTTP {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 找到所有比賽行
        game_rows = soup.find_all('tr', attrs={'gameid': True})
        
        # 分組 (每場比賽有兩行 tr)
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue
            
            # Row 1 = 客隊 (Away), Row 2 = 主隊 (Home)
            r_away = rows[0]
            r_home = rows[1]
            
            # 1. 抓取隊名
            # 隊名在第一行的 td-teaminfo 裡的 a 標籤
            team_td = r_away.find('td', class_='td-teaminfo')
            teams = team_td.find_all('a', target='new')
            
            if len(teams) >= 2:
                away_name_ch = teams[0].text.strip()
                home_name_ch = teams[1].text.strip()
            else:
                continue # 抓不到隊名，跳過
            
            # 轉換為縮寫
            away_abbr = TEAM_MAP.get(away_name_ch, "UNKNOWN")
            home_abbr = TEAM_MAP.get(home_name_ch, "UNKNOWN")
            
            # 2. 抓取不讓分賠率 (td-bank-bet03)
            def extract_odd(row):
                cell = row.find('td', class_='td-bank-bet03')
                if not cell: return np.nan
                
                # 結構通常是 <span class="data-wrap"> ... <span>1.85</span> </span>
                data_wrap = cell.find('span', class_='data-wrap')
                if data_wrap:
                    spans = data_wrap.find_all('span')
                    if spans:
                        txt = spans[-1].text.strip()
                        try:
                            return float(txt)
                        except:
                            return np.nan
                return np.nan

            odd_away = extract_odd(r_away)
            odd_home = extract_odd(r_home)
            
            # 如果兩邊都沒有賠率，通常是這場沒開盤或已取消，我們也記錄下來但賠率為 NaN
            
            daily_data.append({
                'date': f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}", # YYYY-MM-DD
                'game_id_playsport': gid,
                'Away_Abbr': away_abbr,
                'Home_Abbr': home_abbr,
                'Away_Name_CH': away_name_ch,
                'Home_Name_CH': home_name_ch,
                'Odds_Away': odd_away,
                'Odds_Home': odd_home
            })
            
        return daily_data

    except Exception as e:
        print(f"  抓取失敗: {e}")
        return []

# --- 主程式 ---
def main():
    print(f"--- 開始執行 v500: 抓取賠率 ({START_DATE} - {END_DATE}) ---")
    
    # 產生日期列表
    start = datetime.datetime.strptime(START_DATE, "%Y%m%d")
    end = datetime.datetime.strptime(END_DATE, "%Y%m%d")
    date_list = [start + datetime.timedelta(days=x) for x in range(0, (end-start).days + 1)]
    
    all_odds_data = []
    session = requests.Session()
    
    for d in date_list:
        date_str = d.strftime("%Y%m%d")
        
        odds_data = get_odds_for_date(date_str, session)
        if odds_data:
            all_odds_data.extend(odds_data)
            print(f"  -> 找到 {len(odds_data)} 場比賽")
        else:
            print(f"  -> 無比賽或無賠率")
            
        # 禮貌性延遲 (避免被擋)
        time.sleep(2)
        
    # 儲存
    if all_odds_data:
        df = pd.DataFrame(all_odds_data)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig') # 使用 utf-8-sig 以防中文亂碼
        print(f"\n成功！共抓取 {len(df)} 筆賠率數據。")
        print(f"檔案已儲存至: {OUTPUT_FILE}")
        
        # 檢查一下 NaN 的情況
        nan_count = df['Odds_Home'].isna().sum()
        print(f"其中有 {nan_count} 場比賽沒有賠率 (NaN)。")
    else:
        print("未抓取到任何數據。")

if __name__ == "__main__":
    main()