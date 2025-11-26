import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import datetime
import os
import glob
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

def find_latest_prediction_file():
    """
    尋找資料夾中最新的 predictions_YYYY-MM-DD.csv 檔案
    """
    files = glob.glob("predictions_*.csv")
    valid_files = []
    
    pattern = re.compile(r"predictions_(\d{4}-\d{2}-\d{2})\.csv")
    
    for f in files:
        basename = os.path.basename(f)
        if pattern.match(basename):
            valid_files.append(f)
            
    if not valid_files:
        return None
    
    # 排序找最新的
    latest_file = max(valid_files, key=os.path.getctime)
    return latest_file

def get_playsport_odds_robust(target_date_str):
    """
    抓取 PlaySport 指定日期的賠率 (使用 v501.4 強健邏輯)
    """
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
            # 嘗試另一種結構 (有時候是在 table.predictgame-table 下)
            main_table = soup.find('table', class_='predictgame-table')
            if main_table:
                game_rows = main_table.find_all('tr', attrs={'gameid': True})
        
        if not game_rows:
            print("錯誤: 找不到任何比賽行 (gameid)")
            return []
            
        # 2. 根據 gameid 分組
        games_dict = {}
        for row in game_rows:
            gid = row['gameid']
            if gid not in games_dict: games_dict[gid] = []
            games_dict[gid].append(row)
            
        daily_data = []
        
        for gid, rows in games_dict.items():
            if len(rows) < 2: continue 
            
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
                return None

            # 檢查是否兩隊都在第一行
            teams_in_away_row = []
            td_away = r_away.find('td', class_='td-teaminfo')
            if td_away:
                for link in td_away.find_all('a'):
                    txt = link.text.strip()
                    if txt in TEAM_MAP: teams_in_away_row.append(txt)
            
            if len(teams_in_away_row) >= 2:
                # Case A: 兩隊都在第一行
                away_name_ch = teams_in_away_row[0]
                home_name_ch = teams_in_away_row[1]
            else:
                # Case B: 分開在兩行
                away_name_ch = extract_team_name(r_away)
                home_name_ch = extract_team_name(r_home)
            
            if not away_name_ch or not home_name_ch:
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
            
            # print(f"  抓到: {away_name_ch}({away_abbr}) vs {home_name_ch}({home_abbr}) | 賠率: {odd_away} / {odd_home}")
            
            daily_data.append({
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
    print("--- v501: 自動抓取對應賠率 (PlaySport) ---")
    
    # 1. 尋找預測檔案
    pred_file = find_latest_prediction_file()
    
    if not pred_file:
        print("錯誤: 找不到任何 'predictions_YYYY-MM-DD.csv' 檔案。")
        return
        
    print(f"找到最新預測檔案: {pred_file}")
    
    # 2. 解析日期並 +1 天
    try:
        basename = os.path.basename(pred_file)
        match = re.search(r"predictions_(\d{4}-\d{2}-\d{2})\.csv", basename)
        if match:
            date_str = match.group(1)
            pred_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            
            # 【核心邏輯】 台灣時間 = 美國預測日期 + 1 天
            target_date = pred_date + datetime.timedelta(days=1)
            target_date_str = target_date.strftime("%Y%m%d")
            
            print(f"預測日期 (US): {date_str}")
            print(f"目標賠率日期 (TW): {target_date.strftime('%Y-%m-%d')} (+1 day)")
        else:
            print("錯誤: 無法解析日期")
            return
        
    except ValueError:
        print(f"錯誤: 無法從檔名 '{pred_file}' 解析日期。")
        return

    # 3. 抓取賠率
    odds_data = get_playsport_odds_robust(target_date_str)
    
    if odds_data:
        # 4. 儲存 (使用美國日期命名，方便合併)
        output_file = f"odds_for_{date_str}.csv"
        
        df = pd.DataFrame(odds_data)
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n成功！抓取到 {len(df)} 場比賽的賠率。")
        print(f"已儲存至: {output_file}")
        
    else:
        print("\n警告: 未抓取到任何賠率數據。")

if __name__ == "__main__":
    main()