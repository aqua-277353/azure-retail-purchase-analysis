#!/usr/bin/env python3
"""mapper.py (Chỉ dành cho Bảng Khách hàng)"""

import sys
import csv
from datetime import datetime

# Định dạng ngày tháng
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def parse_date(date_str):
    """Phân tích chuỗi ngày tháng và trả về timestamp"""
    try:
        dt = datetime.strptime(date_str, DATE_FORMAT)
        return dt.timestamp()
    except ValueError:
        return None

def main():
    reader = csv.reader(sys.stdin)

    idx_inv_no = 0
    idx_qty = 3
    idx_date = 4
    idx_price = 5
    idx_cust = 6
    idx_country = 7

    try:
        next(reader)
    except StopIteration:
        return

    for row in reader:
        try:
            customer_id = row[idx_cust]
            invoice_no = row[idx_inv_no]
            invoice_date_str = row[idx_date]
            country = row[idx_country]

            if not customer_id:
                continue

            quantity = int(row[idx_qty])
            unit_price = float(row[idx_price])

            if quantity <= 0 or unit_price <= 0:
                continue

            # 1. Tính toán
            total_amount = quantity * unit_price
            timestamp = parse_date(invoice_date_str)
            
            if timestamp is None:
                continue

            # 2. Định dạng giá trị value
            value = f"{total_amount:.2f}\t{invoice_no}\t{timestamp}\t{country}"

            # 3. In ra Key-Value
            # Key = CustomerID
            print(f"{customer_id}\t{value}")

        except (ValueError, IndexError, TypeError) as e:
            sys.stderr.write(f"Mapper: Bỏ qua dòng lỗi: {row}, Lỗi: {e}\n")
            continue

if __name__ == "__main__":
    main()