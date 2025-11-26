import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
import numpy as np
import traceback
import re
import os

def parse_box_score_ultimate(url, session, retries=3, delay=15):
    """
    【v300 Ultimate - 終極解析函式】
    一次性從 Box Score 頁面抓取：
    1. 球隊比賽數據 (Team Stats) & DNP
    2. 球員單場數據 (Player GmSc)
    """
    print(f"  ... 正在解析 {url}")
    
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
    }
    
    response = None
    for attempt in range(retries):
        try:
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status() 
            break 
        except requests.exceptions.RequestException as e:
            print(f"    警告: 訪問 {url} 失敗 (第 {attempt + 1}/{retries} 次嘗試): {e}")
            time.sleep(delay)
            
    if response is None: return None, None
        
    try:
        # --- 1. 獲取基本資訊 ---
        game_date = None; home_team_abbr = None; away_team_abbr = None
        match = re.search(r'/boxscores/(\d{8})0(\w{3})\.html', response.url)
        if match:
            game_date = match.group(1) 
            home_team_abbr = match.group(2) 
        else:
            return None, None

        soup = BeautifulSoup(response.content, 'lxml')
        
        away_team_link = soup.select_one(f'div.scorebox strong a[href*="/teams/"]')
        if away_team_link:
            away_team_match = re.search(r'/teams/(\w{3})/', away_team_link['href'])
            if away_team_match:
                away_team_abbr = away_team_match.group(1)
        
        if not away_team_abbr: return None, None

        game_id = f"{game_date}_{away_team_abbr}_at_{home_team_abbr}"
        
        # === PART A: 球隊數據 ===
        game_data = {'game_id': game_id, 'date': int(game_date), 'home_team': home_team_abbr, 'away_team': away_team_abbr}
        
        # 1. 抓取 DNP
        home_dnp_names = []
        away_dnp_names = []
        
        # (A) 2025 新邏輯 (公開 HTML)
        inactive_div = soup.find('div', string=re.compile(r'Inactive:'))
        if inactive_div:
            home_span = inactive_div.find('span', string=re.compile(home_team_abbr))
            if home_span:
                for sibling in home_span.find_next_siblings():
                    if sibling.name == 'span': break
                    if sibling.name == 'a': home_dnp_names.append(sibling.text.strip())
            away_span = inactive_div.find('span', string=re.compile(away_team_abbr))
            if away_span:
                for sibling in away_span.find_next_siblings():
                    if sibling.name == 'span': break
                    if sibling.name == 'a': away_dnp_names.append(sibling.text.strip())
        
        # (B) 2024 舊邏輯 (註解) - 如果沒找到
        if not home_dnp_names and not away_dnp_names:
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            for comment in comments:
                comment_soup = BeautifulSoup(comment, 'lxml')
                home_dnp_table = comment_soup.find('table', {'id': f'box-{home_team_abbr}-game-basic'})
                if home_dnp_table:
                    dnp_rows = home_dnp_table.find('tfoot').find_all('th', {'data-stat': 'player'})
                    for row in dnp_rows:
                        if "Did Not Play" in row.get('csk', ''): home_dnp_names.append(row.text.strip())
                away_dnp_table = comment_soup.find('table', {'id': f'box-{away_team_abbr}-game-basic'})
                if away_dnp_table:
                    dnp_rows = away_dnp_table.find('tfoot').find_all('th', {'data-stat': 'player'})
                    for row in dnp_rows:
                        if "Did Not Play" in row.get('csk', ''): away_dnp_names.append(row.text.strip())

        game_data['home_dnp'] = ', '.join(home_dnp_names)
        game_data['away_dnp'] = ', '.join(away_dnp_names)

        # 2. 抓取球隊統計 (Tfoot)
        home_table = soup.find('table', {'id': f'box-{home_team_abbr}-game-basic'})
        if home_table and home_table.find('tfoot'):
            home_row = home_table.find('tfoot').find('tr')
            if home_row:
                for stat in ['pts', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']:
                    cell = home_row.find('td', {'data-stat': stat})
                    if cell: game_data[f'home_{stat}'] = int(cell.text)
        
        away_table = soup.find('table', {'id': f'box-{away_team_abbr}-game-basic'})
        if away_table and away_table.find('tfoot'):
            away_row = away_table.find('tfoot').find('tr')
            if away_row:
                for stat in ['pts', 'fg', 'fga', 'fg3', 'fg3a', 'ft', 'fta', 'orb', 'drb', 'trb', 'ast', 'stl', 'blk', 'tov', 'pf']:
                    cell = away_row.find('td', {'data-stat': stat})
                    if cell: game_data[f'away_{stat}'] = int(cell.text)

        # === PART B: 球員數據 (GmSc) ===
        player_gmsc_list = []
        
        # 定義一個內部函式來解析球員表格
        def extract_players_from_table(table, team_code):
            if not table or not table.find('tbody'): return
            for row in table.find('tbody').find_all('tr'):
                if row.has_attr('class') and 'thead' in row['class']: continue
                
                # 必須有 MP (上場時間)，代表有出賽
                mp_cell = row.find('td', {'data-stat': 'mp'})
                if not mp_cell or not mp_cell.text.strip(): continue
                
                # Player Name & ID
                # Name 在 th data-stat="player"
                player_th = row.find('th', {'data-stat': 'player'})
                if not player_th: continue
                
                player_id = player_th.get('data-append-csv') # BBR 這裡直接藏了 ID!
                player_name = player_th.find('a').text if player_th.find('a') else player_th.text
                
                if not player_id: continue # 沒 ID 可能是 Team Totals 或異常
                
                # GmSc
                gmsc_cell = row.find('td', {'data-stat': 'game_score'})
                try:
                    gmsc_val = float(gmsc_cell.text) if gmsc_cell and gmsc_cell.text.strip() else 0.0
                except:
                    gmsc_val = 0.0
                
                # 計算 Season_Year
                # 10,11,12月 -> Year+1, 1-9月 -> Year
                g_year = int(game_date[:4])
                g_month = int(game_date[4:6])
                season_year = g_year + 1 if g_month >= 10 else g_year
                
                player_gmsc_list.append({
                    'Player_ID': player_id,
                    'Player_Name': player_name,
                    'Season_Year': season_year,
                    'Date': f"{game_date[:4]}-{game_date[4:6]}-{game_date[6:]}", # YYYY-MM-DD
                    'Team_Abbr': team_code,
                    'G': 1, # 這裡 G 不重要，重要的是 GmSc
                    'Single_Game_GmSc': gmsc_val
                })

        # 提取主隊球員
        extract_players_from_table(home_table, home_team_abbr)
        # 提取客隊球員
        extract_players_from_table(away_table, away_team_abbr)

        return game_data, player_gmsc_list
        
    except Exception as e:
        print(f"    錯誤: 解析 {url} 出錯: {e}")
        traceback.print_exc()
        return None, None

# --- 【v300-Data 主程式】 ---
def run_v300_data_update():
    print(f"\n--- 開始執行 v300 Ultimate：增量數據抓取 (球隊+球員) ---")
    
    # 1. 檢查新連結
    links_file = "new_links_v300.csv"
    team_target_file = "nba_game_data_raw_v52_PATCHED.csv"
    player_target_file = "nba_player_single_game_gmsc_v52.csv"
    
    if not os.path.exists(links_file):
        print(f"錯誤：找不到 '{links_file}'。請先執行 v300_get_links.py。")
        return

    links_df = pd.read_csv(links_file)
    urls = links_df['box_score_url'].dropna().tolist()
    
    if not urls:
        print("沒有發現新連結。無需更新數據。")
        return

    print(f"發現 {len(urls)} 場新比賽，開始抓取...")
    
    # 2. 開始抓取
    all_new_games = []
    all_new_players = []
    session = requests.Session()
    
    try:
        for i, url in enumerate(urls):
            game_data, players_data = parse_box_score_ultimate(url, session)
            
            if game_data: all_new_games.append(game_data)
            if players_data: all_new_players.extend(players_data)
            
            sleep_time = np.random.uniform(5.0, 8.0)
            print(f"    ... 禮貌性延遲 {sleep_time:.1f} 秒 ...")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n\n--- 爬蟲被手動中止 ---")

    # 3. 追加儲存 (Team Data)
    if all_new_games:
        new_game_df = pd.DataFrame(all_new_games)
        
        # 確保欄位順序
        cols = [
            'game_id', 'date', 'home_team', 'away_team', 'home_dnp', 'away_dnp',
            'home_pts', 'home_fg', 'home_fga', 'home_fg3', 'home_fg3a', 'home_ft', 'home_fta',
            'home_orb', 'home_drb', 'home_trb', 'home_ast', 'home_stl', 'home_blk', 'home_tov', 'home_pf',
            'away_pts', 'away_fg', 'away_fga', 'away_fg3', 'away_fg3a', 'away_ft', 'away_fta',
            'away_orb', 'away_drb', 'away_trb', 'away_ast', 'away_stl', 'away_blk', 'away_tov', 'away_pf'
        ]
        existing_cols = [c for c in cols if c in new_game_df.columns]
        new_game_df = new_game_df[existing_cols]
        
        if os.path.exists(team_target_file):
            print(f"正在追加球隊數據到 '{team_target_file}'...")
            new_game_df.to_csv(team_target_file, mode='a', header=False, index=False)
        else:
            new_game_df.to_csv(team_target_file, index=False)
            
        # 去重
        final_game_df = pd.read_csv(team_target_file)
        final_game_df.drop_duplicates(subset=['game_id'], keep='last', inplace=True)
        final_game_df.to_csv(team_target_file, index=False)
        print(f"球隊數據更新完畢 (總計: {len(final_game_df)} 場)")

    # 4. 追加儲存 (Player Data)
    if all_new_players:
        new_player_df = pd.DataFrame(all_new_players)
        
        if os.path.exists(player_target_file):
            print(f"正在追加球員數據到 '{player_target_file}'...")
            new_player_df.to_csv(player_target_file, mode='a', header=False, index=False)
        else:
            new_player_df.to_csv(player_target_file, index=False)
            
        # 去重
        final_player_df = pd.read_csv(player_target_file)
        final_player_df.drop_duplicates(subset=['Player_ID', 'Date'], keep='last', inplace=True)
        final_player_df.to_csv(player_target_file, index=False)
        print(f"球員數據更新完畢 (總計: {len(final_player_df)} 筆)")
        
    print("\n--- v300 Ultimate 完畢 ---")

if __name__ == "__main__":
    run_v300_data_update()