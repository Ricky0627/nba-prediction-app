import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

def plot_accuracy_chart(input_file):
    print(f"--- 正在繪製準確率折線圖: {input_file} ---")
    
    if not os.path.exists(input_file):
        print(f"錯誤: 找不到檔案 '{input_file}'")
        return

    # 1. 讀取數據
    df = pd.read_csv(input_file)
    
    # 2. 轉換日期格式並排序
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')

    # 3. 計算每日數據
    # Group by date and calculate sum (correct) and count (total)
    daily_stats = df.groupby('date')['Is_Correct'].agg(['sum', 'count']).reset_index()
    daily_stats.columns = ['date', 'correct_count', 'total_count']
    
    # 計算當日勝率
    daily_stats['daily_accuracy'] = daily_stats['correct_count'] / daily_stats['total_count']

    # 4. 計算累積數據 (Total Win Rate)
    daily_stats['cumulative_correct'] = daily_stats['correct_count'].cumsum()
    daily_stats['cumulative_total'] = daily_stats['total_count'].cumsum()
    daily_stats['cumulative_accuracy'] = daily_stats['cumulative_correct'] / daily_stats['cumulative_total']

    # 5. 繪圖
    plt.figure(figsize=(14, 7))
    
    # 繪製當日勝率 (細線，帶圓點，半透明)
    plt.plot(daily_stats['date'], daily_stats['daily_accuracy'], 
             marker='o', linestyle='-', linewidth=1, color='skyblue', alpha=0.7, label='Daily Win Rate')
    
    # 繪製總勝率 (粗線，帶叉號，紅色)
    plt.plot(daily_stats['date'], daily_stats['cumulative_accuracy'], 
             marker='x', linestyle='-', linewidth=3, color='firebrick', label='Total Win Rate (Cumulative)')

    # 加入 50% 基準線
    plt.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)

    # 標題與標籤
    last_acc = daily_stats['cumulative_accuracy'].iloc[-1]
    plt.title(f'NBA 2026 Season Prediction Accuracy (Current Total: {last_acc:.1%})', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Accuracy', fontsize=12)
    plt.ylim(0, 1.05) # 設定 Y 軸範圍 0~100%
    
    # 顯示圖例
    plt.legend(loc='lower right', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # 格式化 X 軸日期
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=3)) # 每 3 天顯示一次
    plt.gcf().autofmt_xdate() # 自動旋轉日期標籤

    # 顯示數值標籤 (只在總勝率線的最後一點顯示)
    last_date = daily_stats['date'].iloc[-1]
    plt.text(last_date, last_acc, f'{last_acc:.1%}', fontsize=12, fontweight='bold', color='firebrick', ha='left', va='bottom')

    # 6. 儲存圖片
    output_img = 'accuracy_chart.png'
    plt.savefig(output_img)
    print(f"圖表已儲存至: '{output_img}'")
    
    # 顯示數據摘要
    print("\n--- 數據摘要 (最近 5 天) ---")
    print(daily_stats[['date', 'daily_accuracy', 'cumulative_accuracy']].tail())

if __name__ == "__main__":
    # 確保檔名正確
    input_csv = "predictions_2026_full_report.csv"
    plot_accuracy_chart(input_csv)