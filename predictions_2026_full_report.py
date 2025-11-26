import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

def predict_2026_season_full(input_file):
    print(f"--- 執行 2026 賽季完整預測與準確率分析 ---")
    
    try:
        df = pd.read_csv(input_file)
        print(f"成功讀取數據: {len(df)} 筆")
    except Exception as e:
        print(f"讀取失敗: {e}")
        return

    # 2. 定義特徵
    feature_columns = [
        'Diff_Days_Since_Last_Game', 'Diff_Before_Game_Streak',
        'Diff_Before_Game_Win_Pct_Last_5', 'Diff_Before_Game_Avg_Margin_Last_5',
        'Diff_Before_Game_Win_Pct_Last_10', 'Diff_CS_Win_Pct_L5', 'Diff_CS_Avg_Margin_L5',
        'Diff_Before_Game_H2H_Win_Pct_L5', 'Diff_Before_Game_H2H_Avg_Margin_L5',
        'Diff_Total_Injury_Impact', 'Diff_Before_Game_Avg_NetRtg',
        'Diff_Before_Game_Avg_TOV_Rate', 'Diff_Before_Game_Avg_ORB_Pct'
    ]
    
    # 檢查欄位
    missing = [c for c in feature_columns if c not in df.columns]
    if missing:
        print(f"錯誤: 缺少欄位 {missing}")
        return

    df = df.fillna(0)

    # 3. 切分訓練 (2016-2025) 與 測試 (2026)
    train_df = df[df['Season_Year'] < 2026].copy()
    test_df = df[df['Season_Year'] == 2026].copy()
    
    if test_df.empty:
        print("錯誤: 找不到 2026 賽季數據")
        return
        
    print(f"訓練集: {len(train_df)} 筆")
    print(f"測試集 (2026): {len(test_df)} 筆")
    
    X_train = train_df[feature_columns]
    y_train = train_df['Win']
    X_test = test_df[feature_columns]
    y_test = test_df['Win']
    
    # 4. 訓練
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)
    print("模型訓練完成")
    
    # 5. 預測
    y_probs = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    # 6. 整理結果
    results = test_df[['date', 'Team_Abbr', 'Opp_Abbr', 'Win']].copy()
    results['Predicted_Win'] = y_pred
    results['Win_Prob'] = y_probs
    results['Is_Correct'] = (results['Win'] == results['Predicted_Win']).astype(int)
    
    # 信心等級
    def get_confidence(prob):
        if prob >= 0.65: return "High (Home)"
        if prob <= 0.35: return "High (Away)"
        return "Normal"
        
    results['Confidence'] = results['Win_Prob'].apply(get_confidence)
    
    # 7. 輸出統計
    acc = accuracy_score(y_test, y_pred)
    print(f"\n2026 賽季總準確率: {acc:.4f} ({results['Is_Correct'].sum()}/{len(results)})")
    
    high_conf = results[results['Confidence'] != "Normal"]
    if not high_conf.empty:
        hc_acc = high_conf['Is_Correct'].mean()
        print(f"高信心場次準確率: {hc_acc:.4f} ({high_conf['Is_Correct'].sum()}/{len(high_conf)})")
        
    # 8. 存檔
    output_file = "predictions_2026_full_report.csv"
    results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n詳細報告已儲存至: {output_file}")

if __name__ == "__main__":
    predict_2026_season_full("FINAL_MASTER_DATASET_v109_FIXED.csv")