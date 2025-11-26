import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import datetime
import re

def get_current_injuries():
    print("--- v400: 正在抓取即時傷病名單 (Current Injuries) ---")
    url = "https://www.basketball-reference.com/friv/injuries.fcgi"
    
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        table = soup.find('table', {'id': 'injuries'})
        if not table:
            print("警告: 找不到傷病表格。")
            return None
            
        injuries = []
        
        # 遍歷每一行
        # 注意：tbody 可能有多個，或者只有一個
        tbody = table.find('tbody')
        if not tbody: return None

        for row in tbody.find_all('tr'):
            # 1. 球員姓名 & ID
            player_cell = row.find('th', {'data-stat': 'player'})
            if not player_cell: continue
            
            player_name = player_cell.text.strip()
            player_link = player_cell.find('a')
            player_id = None
            if player_link:
                # href="/players/n/nfalyda01.html" -> nfalyda01
                match = re.search(r'/players/\w/(\w+)\.html', player_link['href'])
                if match: player_id = match.group(1)
            
            # 2. 球隊 Abbr
            team_cell = row.find('td', {'data-stat': 'team_name'})
            team_abbr = "UNKNOWN"
            if team_cell:
                team_link = team_cell.find('a')
                if team_link:
                    # href="/teams/ATL/2026.html" -> ATL
                    match = re.search(r'/teams/(\w{3})/', team_link['href'])
                    if match: team_abbr = match.group(1)
            
            # 3. 狀態描述 (可選，用於判斷是否真的不能上場)
            note_cell = row.find('td', {'data-stat': 'note'})
            note = note_cell.text.strip() if note_cell else ""
            
            # 簡單過濾：如果 note 包含 "Out For Season" 或 "Out"，我們視為肯定缺席
            # 如果是 "Day To Day"，我們也可以視為缺席 (保守估計)，或者給予 50% 權重
            # 目前我們先全部視為缺席，讓模型自己去判斷
            
            injuries.append({
                'Player_ID': player_id,
                'Player_Name': player_name,
                'Team_Abbr': team_abbr,
                'Note': note,
                'Date_Fetched': datetime.datetime.now().strftime('%Y-%m-%d')
            })
            
        print(f"成功抓取 {len(injuries)} 位受傷球員。")
        
        # 儲存
        df = pd.DataFrame(injuries)
        df.to_csv("current_injuries.csv", index=False)
        print("已儲存至 'current_injuries.csv'")
        
        # 展示前 5 筆
        print(df.head())
        return df
        
    except Exception as e:
        print(f"抓取傷病失敗: {e}")
        return None

if __name__ == "__main__":
    get_current_injuries()