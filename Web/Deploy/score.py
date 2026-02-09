import os
import json
import joblib
import pandas as pd
import numpy as np
import logging

# --- KHAI BÁO BIẾN TOÀN CỤC ---
rfm_data = None
X_scaled = None
model = None # Biến để chứa model K-Means load từ file
init_error = None 

def get_path_simple(base_path, filename):
    """Hàm tìm file (giữ nguyên như cũ vì nó đang hoạt động tốt)"""
    path1 = os.path.join(base_path, filename)
    if os.path.exists(path1): return path1
    
    for folder in os.listdir(base_path):
        sub_folder_path = os.path.join(base_path, folder)
        if os.path.isdir(sub_folder_path):
            path2 = os.path.join(sub_folder_path, filename)
            if os.path.exists(path2): return path2
    return None

def init():
    global rfm_data, X_scaled, model, init_error
    try:
        base_path = os.getenv("AZUREML_MODEL_DIR")
        
        # 1. LOAD DỮ LIỆU GỐC (Để lấy ID khách hàng trả về cho Web)
        csv_path = get_path_simple(base_path, "rfm_data.csv")
        if not csv_path: raise FileNotFoundError("Thiếu file 'rfm_data.csv'")
        rfm_data = pd.read_csv(csv_path)

        # 2. LOAD SCALER (Để chuẩn hóa dữ liệu trước khi đưa vào model)
        scaler_path = get_path_simple(base_path, "scaler.pkl")
        if not scaler_path: raise FileNotFoundError("Thiếu file 'scaler.pkl'")
        scaler = joblib.load(scaler_path)
        
        # Chuẩn hóa dữ liệu sẵn sàng trong RAM
        rfm_features = rfm_data[['Recency', 'Frequency', 'Monetary']]
        X_scaled = scaler.transform(rfm_features)

        # 3. LOAD MODEL K-MEANS (PHẦN MỚI)
        model_path = get_path_simple(base_path, "kmeans_model.pkl")
        if not model_path: raise FileNotFoundError("Thiếu file 'kmeans_model.pkl'")
        model = joblib.load(model_path)
        
        logging.info("INIT THÀNH CÔNG: Đã load Data, Scaler và Model K=3.")

    except Exception as e:
        init_error = str(e)
        logging.error(f"INIT ERROR: {e}")

def run(raw_data):
    # Hàm này không cần input K nữa, chỉ cần gọi là chạy
    global rfm_data, X_scaled, model, init_error

    if init_error: return {"error": init_error}
    if model is None: return {"error": "Model chưa được load."}

    try:
        # --- DỰ ĐOÁN (PREDICT) ---
        # Không dùng fit_predict nữa, mà dùng predict trên model đã có
        clusters = model.predict(X_scaled)
        
        # --- ĐÓNG GÓI KẾT QUẢ ---
        result_list = []
        for i in range(len(rfm_data)):
            result_list.append({
                "customer_id": int(rfm_data.iloc[i]['CustomerID']),
                "recency": float(rfm_data.iloc[i]['Recency']),
                "frequency": float(rfm_data.iloc[i]['Frequency']),
                "monetary": float(rfm_data.iloc[i]['Monetary']),
                "cluster": int(clusters[i])
            })
            
        unique, counts = np.unique(clusters, return_counts=True)
        stats = dict(zip(unique.astype(str), counts.tolist()))

        return {
            "status": "success",
            "k_used": 3, # Cố định là 3
            "chart_data": result_list,
            "stats": stats
        }
    except Exception as e:
        return {"error": str(e)}