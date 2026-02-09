#!/usr/bin/env python3
"""reducer.py (Chỉ dành cho Bảng Khách hàng)"""

import sys
from datetime import datetime

TODAY = datetime(2011, 12, 10, 0, 0)

def main():
    current_key = None

    current_total_amount = 0
    current_invoices = set()
    current_max_timestamp = 0
    current_country = None

    for line in sys.stdin:
        try:
            line = line.strip()
            key, value = line.split('\t', 1)

            if current_key and key != current_key:
                # 1. Tính toán cho khách hàng cũ
                if current_invoices:
                    num_invoices = len(current_invoices)
                    avg_purchase = current_total_amount / num_invoices
                    
                    last_purchase_date = datetime.fromtimestamp(current_max_timestamp)
                    days_since_last = (TODAY - last_purchase_date).days
                    
                    # 2. In kết quả của khách hàng CŨ
                    output = (
                        f"MaKH: {current_key}\tQuocGia: {current_country}\t"
                        f"TongTien: {current_total_amount:.2f}\tSoHoaDon: {num_invoices}\t"
                        f"NgayCuoiMua: {days_since_last}\tTB_Mua: {avg_purchase:.2f}"
                    )
                    print(output)
                
                # 3. Reset cho khách hàng MỚI
                current_total_amount = 0
                current_invoices = set()
                current_max_timestamp = 0
                current_country = None

            current_key = key
            
            # Tích lũy dữ liệu cho khách hàng hiện tại
            try:
                parts = value.split('\t')
                current_total_amount += float(parts[0])
                current_invoices.add(parts[1]) 
                current_max_timestamp = max(current_max_timestamp, float(parts[2]))
                if not current_country:
                    current_country = parts[3]
            except (ValueError, IndexError) as e:
                sys.stderr.write(f"Reducer: Bỏ qua dữ liệu value lỗi: {value}, Lỗi: {e}\n")

        except Exception as e:
            sys.stderr.write(f"Reducer: Lỗi dòng nghiêm trọng: {line}, Lỗi: {e}\n")
            continue

    try:
        if current_key and current_invoices:
            num_invoices = len(current_invoices)
            avg_purchase = current_total_amount / num_invoices
            
            last_purchase_date = datetime.fromtimestamp(current_max_timestamp)
            days_since_last = (TODAY - last_purchase_date).days
            
            output = (
                f"MaKH: {current_key}\tQuocGia: {current_country}\t"
                f"TongTien: {current_total_amount:.2f}\tSoHoaDon: {num_invoices}\t"
                f"NgayCuoiMua: {days_since_last}\tTB_Mua: {avg_purchase:.2f}"
            )
            print(output)
    except Exception as e:
        sys.stderr.write(f"Reducer: Lỗi khi flush khách hàng cuối cùng {current_key}: {e}\n")

if __name__ == "__main__":
    main()