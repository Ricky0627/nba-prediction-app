import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import numpy as np
import traceback
import os
from datetime import datetime, timedelta

def get_links_for_date(date_obj):
    """
    【v300 - 增量核心】
    抓取指定日期 (YYYY-MM-DD) 的所有 Box Score 連結。
    來源: https://www.basketball-reference.com/boxscores/?month=10&day=22&year=2025
    """
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    
    url = f"https://www.basketball-reference.com/boxscores/?month={month}&day={day}&year={year}"
    print(f"  ... 正在檢查日期: {date_obj.strftime('%Y-%m-%d')} (來源: {url})")
    
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
    
    links = []
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        # 找到所有 "Box Score" 連結
        # BBR 的結構是：在每個比賽的表格下方有一個 "Box Score" 連結
        for link in soup.find_all('a', string='Box Score'):
            href = link.get('href')
            if href:
                full_url = f"https://www.basketball-reference.com{href}"
                links.append(full_url)
                
        print(f"    -> 找到 {len(links)} 場比賽。")
        return links

    except Exception as e:
        print(f"    錯誤: 無法抓取 {date_obj.strftime('%Y-%m-%d')} 的賽程: {e}")
        return []

# --- 【v300 執行】 ---
print(f"\n--- 開始執行 v300：增量連結抓取 (Smart Update) ---")

# 1. 讀取現有數據，找出最後更新日期
current_data_file = "nba_game_data_raw_v52_PATCHED.csv"
if not os.path.exists(current_data_file):
    print(f"錯誤：找不到 '{current_data_file}'。請先完成 v200 流程。")
    exit()

df_existing = pd.read_csv(current_data_file)
# 轉換日期格式 (假設是 YYYYMMDD)
df_existing['date_dt'] = pd.to_datetime(df_existing['date'].astype(str), format='%Y%m%d')
last_date = df_existing['date_dt'].max()

print(f"目前數據庫最後日期: {last_date.strftime('%Y-%m-%d')}")

# 2. 設定抓取範圍：從 (最後日期 + 1天) 到 (今天)
today = datetime.now()
# 如果最後日期是今天，代表已經最新了，但為了保險（可能今天稍早只抓了一半），我們還是檢查今天
start_date = last_date + timedelta(days=1) 
end_date = today

if start_date.date() > end_date.date():
    print("數據已經是最新的！無需更新連結。")
    # 產生一個空的 CSV 以免後續腳本報錯
    pd.DataFrame(columns=['box_score_url']).to_csv('new_links_v300.csv', index=False)
    exit()

print(f"準備更新日期範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")

# 3. 循環日期抓取連結
all_new_links = []
current_date = start_date
while current_date.date() <= end_date.date():
    links = get_links_for_date(current_date)
    if links:
        all_new_links.extend(links)
    
    # 禮貌性延遲
    time.sleep(np.random.uniform(2.0, 4.0))
    current_date += timedelta(days=1)

# 4. 儲存新連結
output_filename = 'new_links_v300.csv'
if all_new_links:
    # 去除重複
    unique_links = sorted(list(set(all_new_links)))
    links_df = pd.DataFrame(unique_links, columns=['box_score_url'])
    links_df.to_csv(output_filename, index=False)
    
    print(f"\n--- v300 連結抓取完畢 ---")
    print(f"成功找到 {len(unique_links)} 個【全新】比賽連結。")
    print(f"已儲存至: '{output_filename}'")
else:
    print(f"\n--- v300 連結抓取完畢 ---")
    print("這段期間沒有任何新比賽 (可能是休賽日或尚未開打)。")
    # 產生空檔案
    pd.DataFrame(columns=['box_score_url']).to_csv(output_filename, index=False)