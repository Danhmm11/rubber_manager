
import requests
from bs4 import BeautifulSoup
import pymysql
from datetime import datetime

# Cấu hình kết nối MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'quocdanh',  # Thay bằng mật khẩu của bạn
    'database': 'project',  # Thay bằng tên database của bạn
    'charset': 'utf8mb4'
}

def get_rubber_price():
    url = "https://www.thitruonghanghoa.com/gia-hang-hoa/gia-cao-su-the-gioi?period=3m&notation=3&compare=2024"
    response = requests.get(url)
    print(response.status_code)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        price_span = soup.find('span', class_='current-price')
        print(price_span)
        if price_span:
            
            return convert_vietnamese_number(price_span.text.strip().split()[0])  # Lấy giá trị số
    return None

def update_price_in_db(price):
    
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    today = datetime.now().date()
    try:
        # Kiểm tra nếu đã có giá cho hôm nay
        cursor.execute("SELECT COUNT(*) FROM price WHERE day = %s", (today,))
        if cursor.fetchone()[0] > 0:
            # Nếu có, cập nhật giá
            cursor.execute("UPDATE price SET price = %s WHERE day = %s", (price, today))
        else:
            # Nếu không có, thêm mới
            cursor.execute("INSERT INTO price (day, price) VALUES (%s, %s)", (today, price))
        conn.commit()
        print(f"Đã cập nhật giá cho ngày {today}: {price}")
    except Exception as e:
        print(f"Lỗi khi cập nhật cơ sở dữ liệu: {e}")
    finally:
        cursor.close()
        conn.close()
def convert_vietnamese_number(num_str):
    """
    Chuyển đổi chuỗi số có dấu chấm (phân cách hàng nghìn kiểu Việt Nam) thành số nguyên.
    """
    # Loại bỏ dấu chấm
    cleaned_number = num_str.replace('.', '')
    # Chuyển chuỗi thành số nguyên
    try:
        return float(cleaned_number)
    except ValueError:
        raise ValueError(f"Giá trị '{num_str}' không phải là một số hợp lệ.")
if __name__ == "__main__":
    price = get_rubber_price()
    if price:
        update_price_in_db(price)
    else:
        print("Không thể lấy giá cao su từ trang web.")
