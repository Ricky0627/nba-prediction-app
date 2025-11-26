import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.calibration import calibration_curve
import warnings

# 忽略 FutureWarning
warnings.simplefilter(action='ignore', category=FutureWarning)

def analyze_calibration():
    print("--- v850: 模型校準度分析 (Calibration Check) ---")
    
    # 1. 載入 2026 賽季的驗證報告
    input_file = "predictions_2026_full_report.csv"
    
    if not os.path.exists(input_file):
        print(f"錯誤: 找不到 '{input_file}'")
        print("請先執行 'v500_export_predictions.py' 或重新跑一次模型驗證來產生此檔案。")
        return

    df = pd.read_csv(input_file)
    print(f"成功讀取 {len(df)} 場比賽數據。")
    
    if 'Win_Prob' not in df.columns or 'Win' not in df.columns:
        print("錯誤: 檔案欄位不符 (需要 'Win_Prob' 和 'Win')")
        return

    # 2. 計算校準曲線
    prob_true, prob_pred = calibration_curve(df['Win'], df['Win_Prob'], n_bins=10, strategy='uniform')

    # 3. 數據分析準備
    bins = np.linspace(0, 1, 11)
    df['prob_bin'] = pd.cut(df['Win_Prob'], bins=bins, include_lowest=True)
    
    # 統計每個區間的數據
    grouped = df.groupby('prob_bin')['Win'].agg(['mean', 'count'])
    grouped['pred_mean'] = df.groupby('prob_bin')['Win_Prob'].mean()
    
    # 顯示表格
    print("\n" + "="*60)
    print(f"{'預測機率區間':<15} | {'實際勝率':<10} | {'場次':<6} | {'偏差 (預測-實際)'}")
    print("-" * 60)
    
    sweet_spots = []
    danger_zones = []
    
    # 迭代所有區間顯示表格
    for i in range(len(grouped)):
        count = grouped['count'].iloc[i]
        if count > 0:
            pred_avg = grouped['pred_mean'].iloc[i]
            true_avg = grouped['mean'].iloc[i]
            diff = pred_avg - true_avg
            
            bin_str = f"{bins[i]:.1f} - {bins[i+1]:.1f}"
            marker = ""
            
            if abs(diff) < 0.05: marker = "✅ 精準"
            elif diff > 0.10:    marker = "⚠️ 過度自信 (危險)"
            elif diff < -0.10:   marker = "💎 過度謙虛 (機會)"
            
            print(f"{bin_str:<15} | {true_avg:.1%}    | {count:<6} | {diff:+.1%}  {marker}")
            
            # 策略收集
            if count >= 5: # 門檻稍微降低一點以便觀察
                if true_avg > 0.7:
                    if diff < 0.05: sweet_spots.append(f"主勝穩膽區 ({bin_str})")
                if true_avg < 0.3:
                    if diff > -0.05: sweet_spots.append(f"客勝狙擊區 ({bin_str})")
                if diff > 0.15: danger_zones.append(f"主隊過熱區 ({bin_str})")

    print("="*60)
    
    print("\n[🤖 v850 策略建議]")
    if sweet_spots:
        print("🎯 甜蜜點 (值得重注):")
        for s in sweet_spots: print(f"  - {s}")
    else:
        print("  (無明顯甜蜜點)")
        
    if danger_zones:
        print("\n💀 危險區 (建議避開或反下):")
        for d in danger_zones: print(f"  - {d}")

    # 4. 繪圖
    plt.figure(figsize=(10, 8))
    plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfectly Calibrated')
    plt.plot(prob_pred, prob_true, marker='o', linewidth=2, label='Model (v114)')
    
    plt.title('Reliability Diagram (Calibration Curve)', fontsize=16)
    plt.xlabel('Predicted Probability (Confidence)', fontsize=12)
    plt.ylabel('Actual Win Rate', fontsize=12)
    plt.legend(loc='lower right')
    plt.grid(True, alpha=0.3)
    
    # 5. 【修正】安全的標註邏輯
    # 我們只取出有數據的區間 (count > 0)，這些區間會直接對應到 prob_pred 的點
    non_empty_bins = grouped[grouped['count'] > 0]
    
    # 確保長度一致 (理論上 calibration_curve 返回的點數 = 非空區間數)
    if len(prob_pred) == len(non_empty_bins):
        for i in range(len(prob_pred)):
            count = non_empty_bins['count'].iloc[i]
            # 在點的上方標註場次 n=...
            plt.text(prob_pred[i], prob_true[i] + 0.02, f"n={count}", 
                     ha='center', fontsize=9, color='blue', fontweight='bold')
    else:
        print("\n(繪圖提示: 預測點與區間數不匹配，跳過標註)")

    output_img = 'calibration_chart.png'
    plt.savefig(output_img)
    print(f"\n📊 校準曲線圖已儲存至: '{output_img}'")
    print("請打開圖片查看：")
    print("- 線在對角線下方 = 模型過度自信 (賠率可能不好)")
    print("- 線在對角線上方 = 模型過度謙虛 (可能有超額利潤)")

if __name__ == "__main__":
    analyze_calibration()