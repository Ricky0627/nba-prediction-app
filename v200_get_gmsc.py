import requests
from bs4 import BeautifulSoup, Comment 
import pandas as pd
import time
import numpy as np
import traceback
import re
import os
import io 

def parse_player_gamelog_gmsc_v51_12(player_id, player_name, season_year, session, retries=3, delay=20):
    """
    【v51.12 - 核心 GmSc 解析函式 (2025-11-15 修正版)】
    1. 使用 Requests
    2. 尋找表格 ID: 'player_game_log_reg' (仍然正確)
    3. 回退 (fallback) 尋找 'pgl_basic' (仍然正確)
    4. 【!! 2025-11-15 核心修正 !!】
       - 將 'data-stat': 'g' (不存在) -> 'data-stat': 'ranker' (存在於 <th>)
       - 將 'data-stat': 'date_game' (不存在) -> 'data-stat': 'date'
       - 將 'data-stat': 'team_id' (不存在) -> 'data-stat': 'team_name_abbr'
    5. 【!! v201 核心修正 !!】
       - 將 timeout 從 15 秒增加到 30 秒
    """
    url = f"https://www.basketball-reference.com/players/{player_id[0]}/{player_id}/gamelog/{season_year}"
    print(f"  ... 正在解析 {player_name} ({player_id}) {season_year} 賽季 GmSc...")
    
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive'
    }
    
    response = None 
    for attempt in range(retries):
        try:
            # 【!! v201 核心修正 !!】 增加超時時間
            response = session.get(url, headers=headers, timeout=30) 
            response.raise_for_status() 
            break 
        except requests.exceptions.RequestException as e:
            print(f"      警告: 訪問 {url} 失敗 (第 {attempt + 1}/{retries} 次嘗試): {e}")
            if attempt < retries - 1:
                wait_time = delay * (attempt + 1)
                print(f"      ... 將在 {wait_time} 秒後重試 ...")
                time.sleep(wait_time)
            else:
                print(f"      錯誤: 重試 {retries} 次後仍然失敗，放棄此球員/賽季。")
                return []
    
    if response is None:
        return []

    player_game_logs = []
    
    try:
        soup = BeautifulSoup(response.content, 'lxml')
        
        table = soup.find('table', {'id': 'player_game_log_reg'}) 
        
        if not table:
            table = soup.find('table', {'id': 'pgl_basic'})
            
            if not table:
                print(f"      (提示: 在 {player_name} {season_year} 頁面找不到 'player_game_log_reg' 或 'pgl_basic' 表格。跳過)")
                return []
                
        tbody = table.find('tbody')
        if not tbody:
            print(f"      警告: 找不到 'tbody'。")
            return []

        rows = tbody.find_all('tr')
        for row in rows:
            if row.has_attr('class') and 'thead' in row['class']:
                continue

            # 【!! v51.12 修正 1 !!】
            g_cell = row.find('th', {'data-stat': 'ranker'})

            if not g_cell or g_cell.text.strip() == '':
                continue 
            
            try:
                g_value = int(g_cell.text)
            except ValueError:
                continue 

            gmsc_cell = row.find('td', {'data-stat': 'game_score'})
            if not gmsc_cell or gmsc_cell.text.strip() == '':
                continue 
            
            try:
                gmsc_value = float(gmsc_cell.text)
            except ValueError:
                gmsc_value = 0.0 

            # 【!! v51.12 修正 2 !!】
            date_cell = row.find('td', {'data-stat': 'date'})
            
            if not date_cell or not date_cell.find('a'):
                continue
            game_date = date_cell.find('a').text.strip()

            # 【!! v51.12 修正 3 !!】
            team_cell = row.find('td', {'data-stat': 'team_name_abbr'}) 
            if not team_cell:
                team_cell = row.find('td', {'data-stat': 'team_id'}) 
            if not team_cell:
                team_cell = row.find('td', {'data-stat': 'tm'}) 
            
            team_abbr = team_cell.text.strip() if team_cell else "UNKNOWN"

            player_game_logs.append({
                'Player_ID': player_id,
                'Player_Name': player_name,
                'Season_Year': season_year,
                'Date': game_date,
                'Team_Abbr': team_abbr,
                'G': g_value,
                'Single_Game_GmSc': gmsc_value
            })
            
    except Exception as e:
        print(f"      錯誤: 解析 {url} 的 HTML 內容時出錯: {e}")
        traceback.print_exc()

    return player_game_logs

# --- 【v201-GmSc 執行 (v51.12 + 中斷續爬)】 ---
player_list_file = 'nba_player_list.csv'
output_filename = 'nba_player_single_game_gmsc_NEW.csv' # 只儲存新數據

if not os.path.exists(player_list_file):
    print(f"錯誤：找不到 '{player_list_file}'。")
    print("請先執行 'v200_get_players.py' (第 5a 步)。")
    exit()

# --- 【v201 核心 - 讀取進度】 ---
existing_player_ids = set()
all_player_gmsc_data = []

if os.path.exists(output_filename):
    try:
        df_existing_data = pd.read_csv(output_filename)
        if not df_existing_data.empty:
            existing_player_ids = set(df_existing_data['Player_ID'].unique())
            # 載入舊數據，以便稍後一起儲存
            all_player_gmsc_data = df_existing_data.to_dict('records') 
            print(f"已讀取 {len(all_player_gmsc_data)} 筆記錄，{len(existing_player_ids)} 位球員。將從中斷處繼續。")
        else:
            print(f"'{output_filename}' 是空的。將從頭開始。")
    except pd.errors.EmptyDataError:
        print(f"'{output_filename}' 是空的。將從頭開始。")
    except Exception as e:
        print(f"讀取 '{output_filename}' 失敗 ({e})。將重新開始（舊檔案將被覆蓋）。")
        all_player_gmsc_data = [] # 清空以防萬一
else:
    print(f"未偵測到 '{output_filename}'。將從頭開始。")
# --- 【v201 核心 - 讀取完畢】 ---


print(f"\n--- 開始執行 v201 (第 5b 步, v51.12 + 續爬)：抓取 2025 & 2026 賽季 GmSc ---")
df_players_all = pd.read_csv(player_list_file)

# --- (v51.7 核心) 只篩選 2025 或 2026 賽季有上場的球員 ---
df_players_active = df_players_all[df_players_all['Year_Max'] >= 2025].copy()
total_players_all = len(df_players_all)
total_players_active = len(df_players_active)

print(f"已從 {total_players_all} 位總球員中，篩選出 {total_players_active} 位在 2025/2026 賽季活躍的球員。")

SEASONS = [2025, 2026] 
session = requests.Session()

try:
    # 遍歷「活躍球員」 (df_players_active)
    for i, player in df_players_active.iterrows():
        player_id = player['Player_ID']
        player_name = player['Player_Name']
        
        # --- 【v201 核心 - 檢查進度】 ---
        if player_id in existing_player_ids:
            print(f"--- (進度 {i+1}/{total_players_active}) 已在 '{output_filename}' 中找到 {player_name} ({player_id})，跳過 ---")
            continue
        # --- 【v201 核心 - 檢查完畢】 ---
        
        try:
            year_max_cutoff = int(player['Year_Max']) + 1 
        except ValueError:
            print(f"警告: {player_name} 的年份無法轉換，跳過。")
            continue
        
        print(f"\n---  intransite 正在處理球員 {i+1}/{total_players_active}: {player_name} ({player_id}) [生涯: {player.Year_Min}-{player.Year_Max}] ---")
        
        for season in SEASONS:
            if season <= year_max_cutoff: 
                # 【!! v51.12 核心 !!】 
                gmsc_data = parse_player_gamelog_gmsc_v51_12(player_id, player_name, season, session) 
                
                if gmsc_data:
                    all_player_gmsc_data.extend(gmsc_data) 
                
                # --- 【!! v201 核心修正 !!】 延長延遲 (避免 DNS 封鎖) ---
                sleep_time = np.random.uniform(15.0, 25.0) # <--- 增加延遲
                print(f"      ... 禮貌性延遲 {sleep_time:.1f} 秒 ...")
                time.sleep(sleep_time)
            else:
                pass 
                
        # 臨時儲存 (以防腳本中斷)
        if (i+1) % 50 == 0:
            print(f"\n--- 正在執行臨時儲存 (進度 {i+1}/{total_players_active}) ---")
            # 儲存時，我們使用 'all_player_gmsc_data'，它現在包含了舊數據 + 新數據
            temp_df = pd.DataFrame(all_player_gmsc_data)
            
            # 臨時儲存前也移除重複，保持檔案乾淨
            temp_df.drop_duplicates(subset=['Player_ID', 'Date'], keep='last', inplace=True)
            
            temp_df.to_csv(output_filename, index=False)
            print(f"已臨時儲存 {len(temp_df)} 筆數據到 '{output_filename}'")
            
except KeyboardInterrupt:
    print("\n\n--- 爬蟲被手動中止 (KeyboardInterrupt) ---")
    print("正在儲存目前已抓取到的數據...")
except Exception as e_main:
    print(f"\n--- 【!! 嚴重錯誤 !!】 爬蟲主迴圈發生未知錯誤 ---")
    print(e_main)
    traceback.print_exc()

finally:
    # --- 儲存 ---
    if all_player_gmsc_data: 
        master_gmsc_df = pd.DataFrame(all_player_gmsc_data) 
        
        columns_order = ['Player_ID', 'Player_Name', 'Season_Year', 'Date', 'Team_Abbr', 'G', 'Single_Game_GmSc']
        
        # 確保新欄位存在，如果舊檔案沒有的話 (雖然在這個腳本中不太可能，但是個好習慣)
        for col in columns_order:
            if col not in master_gmsc_df.columns:
                master_gmsc_df[col] = np.nan
                
        master_gmsc_df = master_gmsc_df[columns_order]
        
        master_gmsc_df = master_gmsc_df.sort_values(by=['Player_ID', 'Date'])
        
        # 移除重複 (這是最後的保險，確保資料乾淨)
        master_gmsc_df.drop_duplicates(subset=['Player_ID', 'Date'], keep='last', inplace=True)
        
        master_gmsc_df.to_csv(output_filename, index=False)
        
        print(f"\n--- 第 5b 步 完畢 ---")
        print(f"成功將 {len(master_gmsc_df)} 筆【總共】的 GmSc 數據儲存到: '{output_filename}'")
        print(f"\n您的下一步是執行「v200_merge_gmsc.py」。")
    else:
        print("\n--- 第 5b 步 失敗 ---")
        print("未抓取到任何新的 GmSc 數據。")