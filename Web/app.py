import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

# --- CẤU HÌNH API ---
ENDPOINT_URL = ""
API_KEY = ""

st.set_page_config(layout="wide", page_title="RFM 3D Clustering")

# --- HEADER ---
st.title("📊 Phân Tích Khách Hàng 3D (Static K-Means)")
st.markdown("Hệ thống sử dụng mô hình AI đã được huấn luyện sẵn trên Azure Cloud.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🚀 Điều khiển")
    st.info("Mô hình đã được cố định số lượng nhóm (K).")

    run_btn = st.button("Tải dữ liệu & Phân tích", type="primary")
    
    st.divider()
    st.caption("Backend: Azure Machine Learning")

# --- LOGIC CHÍNH ---
if run_btn:
    with st.spinner("Đang kết nối đến Azure Endpoint..."):
        try:
            # 1. Gửi Request (dummy)
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            }
            # Gửi dummy data vì score.py không cần input, nhưng Azure bắt buộc phải có body
            payload = {"k": 0} 
            
            response = requests.post(ENDPOINT_URL, json=payload, headers=headers)
            
            # 2. Xử lý kết quả
            if response.status_code == 200:
                result = response.json()
                
                # Kiểm tra lỗi logic từ score.py
                if "error" in result:
                    st.error(f"❌ Lỗi từ Server: {result['error']}")
                else:
                    # Lấy dữ liệu thành công
                    k_used = result.get('k_used', 'N/A')
                    chart_data = result.get('chart_data', [])
                    stats = result.get('stats', {})
                    
                    st.success(f"✅ Phân tích thành công! Dữ liệu được chia thành **{k_used} nhóm**.")
                    
                    # 3. Vẽ biểu đồ
                    if chart_data:
                        df = pd.DataFrame(chart_data)
                        
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.subheader(f"Mô hình không gian 3 chiều (K={k_used})")
                            fig = px.scatter_3d(
                                df, 
                                x='recency', 
                                y='frequency', 
                                z='monetary',
                                color=df['cluster'].astype(str), 
                                hover_data=['customer_id'],
                                title="Giữ chuột trái để xoay - Lăn chuột để phóng to",
                                opacity=0.7, 
                                size_max=10
                            )
                            fig.update_layout(height=600, margin=dict(l=0, r=0, b=0, t=30))
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            st.subheader("Thống kê chi tiết")
                            # Bảng số liệu
                            stats_df = pd.DataFrame(list(stats.items()), columns=['Nhóm', 'Số lượng'])
                            stats_df = stats_df.sort_values(by='Nhóm')
                            st.dataframe(stats_df, hide_index=True)
                            
                            # Biểu đồ tròn
                            fig_pie = px.pie(stats_df, values='Số lượng', names='Nhóm', hole=0.3)
                            fig_pie.update_layout(height=300, margin=dict(l=0, r=0, b=0, t=0))
                            st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.warning("API trả về dữ liệu rỗng.")
            else:
                st.error(f"❌ Lỗi HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            st.error(f"❌ Không thể kết nối: {e}")

else:
    # Màn hình chờ khi chưa bấm nút
    st.info("👈 Bấm nút **'Tải dữ liệu & Phân tích'** bên trái để bắt đầu.")