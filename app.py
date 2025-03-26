from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
import pymysql.cursors
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import mysql.connector
import logging
import json

from flask_mail import Mail, Message
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

# Cấu hình kết nối MySQL
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'your_password',  # Thay bằng mật khẩu MySQL của bạn
    'database': 'rubber',  # Thay bằng tên database của bạn
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}
#--------------------------------------------------------------------------------------------------------------------------

def get_user_transactions(user_id):
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    u.full_name AS user_name,
                    h.date,
                    h.hàm_lượng AS ham_luong,
                    h.khối_lượng AS khoi_luong,
                    p.price AS gia,
                    (h.khối_lượng * h.hàm_lượng / 100 * p.price) AS thanh_tien
                FROM hàm_lượng h
                JOIN user u ON h.user_id = u.user_id
                JOIN price p ON h.date = p.day
                WHERE u.user_id = %s
                ORDER BY h.date DESC;
            """
            cursor.execute(query, (user_id,))
            transactions = cursor.fetchall()
    finally:
        conn.close()

    return transactions

def generate_user_id():
    """
    Sinh user_id mới dựa trên giá trị lớn nhất trong database.
    """
    try:
        with pymysql.connect(**db_config) as conn:
            cursor = conn.cursor()
            # Lấy giá trị user_id lớn nhất trong bảng
            cursor.execute("SELECT MAX(user_id) FROM user")
            result = list(cursor.fetchone().values())[0]
            
            
            if result is None:  # Nếu bảng rỗng, bắt đầu từ 1
                next_id = 1
            else:
                next_id = result + 1  # Tăng thêm 1 so với giá trị lớn nhất

            if next_id > 999:  # Giới hạn tối đa là 3 chữ số
                raise ValueError("Đã hết ID khả dụng (vượt quá 3 chữ số).")

            return next_id
    except pymysql.MySQLError as err:
        logging.error(f"Lỗi MySQL: {err}")
        return None
# Hàm lấy vai trò của người dùng từ database
def get_all_users():
    # Kết nối cơ sở dữ liệu
    conn = pymysql.connect(**db_config)
    try:
        with conn.cursor() as cursor:
        
        # Truy vấn lấy tất cả người dùng
            cursor.execute("SELECT * FROM user")  # Lấy tất cả thông tin người dùng từ bảng 'user'

            # Lấy tất cả kết quả
            users = cursor.fetchall()
            
            # Đóng kết nối
            
    finally:
    # Đảm bảo đóng kết nối ngay cả khi có lỗi
        conn.close()
    return users

def get_all_transactions():
    conn = pymysql.connect(**db_config)
    with conn.cursor() as cursor:
        query = """
            SELECT 
                u.full_name AS user_name,
                h.date,
                h.hàm_lượng AS ham_luong,
                h.khối_lượng AS khoi_luong,
                p.price AS gia,
                (h.khối_lượng * h.hàm_lượng / 100 * p.price) AS thanh_tien
            FROM hàm_lượng h
            JOIN user u ON h.user_id = u.user_id
            JOIN price p ON h.date = p.day
            ORDER BY h.date DESC;
        """
        cursor.execute(query)
        transactions = cursor.fetchall()
        print(transactions)
    conn.close()
    return transactions


def get_user_role(user_id):
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            query = "SELECT role FROM login WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
        if result:
            return result['role']
        return None
    except pymysql.MySQLError as e:
        print(f"Lỗi MySQL: {e}")
        return None
    finally:
        if conn:
            conn.close()


#--------------------------------------------------------------------------------------------------------------
# Trang đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = pymysql.connect(**db_config)
            with conn.cursor() as cursor:
                query = "SELECT * FROM login WHERE username = %s AND password = %s"
                cursor.execute(query, (username, password))
                user = cursor.fetchone()

            if user:
                session['user_id'] = user['user_id']

                # Điều hướng theo vai trò người dùng
                user_role = get_user_role(user['user_id'])
                if user_role == 'manager':
                    flash('Đăng nhập thành công, chào mừng Quản lý!', 'success')
                    return redirect(url_for('manager_dashboard'))
                elif user_role == 'customer':
                    flash('Đăng nhập thành công, chào mừng Khách hàng!', 'success')
                    return redirect(url_for('customer_dashboard'))
                else:
                    flash('Role không hợp lệ!', 'danger')
                    return redirect(url_for('login'))
            else:
                flash('Sai tên đăng nhập hoặc mật khẩu!', 'danger')
        except pymysql.MySQLError as e:
            flash(f"Lỗi cơ sở dữ liệu: {e}", 'danger')
        finally:
            if conn:
                conn.close()

    return render_template('index.html')
#--------------------------------------------------------------------------------------------------------------

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'example@gmail.com'
    app.config['MAIL_PASSWORD'] = 'example'  # App Password.

    mail = Mail(app)
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cursor:
                # Kiểm tra thông tin người dùng
                query = """
                SELECT * FROM user 
                WHERE full_name = %s AND email = %s AND phone = %s
                """
                cursor.execute(query, (full_name, email, phone))
                user = cursor.fetchone()

                if user:
                    # Tạo mã xác thực
                    verification_code = str(random.randint(100000, 999999))
                    session['verification_code'] = verification_code
                    session['user_id'] = user['user_id']

                    # Gửi mã xác thực qua email
                    msg = Message('Mã xác thực lấy lại mật khẩu', sender='your_email@gmail.com', recipients=[email])
                    msg.body = f"Mã xác thực của bạn là: {verification_code}"
                    mail.send(msg)

                    flash('Mã xác thực đã được gửi đến email của bạn.', 'success')
                    return redirect(url_for('verify_code'))
                else:
                    flash('Thông tin không chính xác. Vui lòng thử lại.', 'danger')
        finally:
            conn.close()
    return render_template('forgot_password.html')

@app.route('/verify_code', methods=['GET', 'POST'])
def verify_code():
    if request.method == 'POST':
        input_code = request.form.get('verification_code')
        if input_code == session.get('verification_code'):
            return redirect(url_for('reset_password'))
        else:
            flash('Mã xác thực không chính xác.', 'danger')
    return render_template('verify_code.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        user_id = session.get('user_id')

        conn = pymysql.connect(**db_config)
        try:
            with conn.cursor() as cursor:
                # Cập nhật mật khẩu
                query = """
                UPDATE login 
                SET password = %s 
                WHERE user_id = %s
                """
                cursor.execute(query, (new_password, user_id))
                conn.commit()
                flash('Mật khẩu của bạn đã được cập nhật.', 'success')
                return redirect(url_for('forgot_password'))
        finally:
            conn.close()
    return render_template('reset_password.html')

#-----------------------------------------------------------------------------------------------------------------------------------


@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        rfid = request.form['rfid']

        # Kiểm tra nếu các trường bắt buộc bị thiếu
        if not username or not password or not full_name or not email or not phone or not rfid:
            return jsonify({'status': 'error', 'message': 'Vui lòng nhập đầy đủ thông tin.'}), 400
        
        # Tạo user_id mới
        user_id = generate_user_id()
        if user_id is None:
            return jsonify({'status': 'error', 'message': 'Không thể tạo user_id mới.'}), 500

        try:
            conn = pymysql.connect(**db_config)
            with conn.cursor() as cursor:
                # Thêm vào bảng `user`
                user_query = """
                    INSERT INTO user ( full_name, email, phone, rfid)
                    VALUES (, %s, %s, %s, %s)
                """
                cursor.execute(user_query, (full_name, email, phone, rfid))

                # Thêm vào bảng `login`
                login_query = """
                    INSERT INTO login ( username, password, role)
                    VALUES ( %s, %s, %s)
                """
                cursor.execute(login_query, ( username, password, role))

            conn.commit()

            # Trả về thông báo thành công
            return jsonify({'status': 'success', 'message': 'Đã thêm người dùng thành công!'}), 200

        except pymysql.MySQLError as e:
            # Trả về thông báo lỗi
            return jsonify({'status': 'error', 'message': f'Lỗi khi thêm người dùng: {e}'}), 500
        
        finally:
            if conn:
                conn.close()

    # Nếu phương thức là GET, trả về form thêm người dùng
    return render_template("add_customer.html")



#-------------------------------------------------------------------------------------------------------------------------------
#customer_dashboard
@app.route('/customer_dashboard')
def customer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']  # Lấy user_id từ session
   
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # Lấy thông tin giao dịch
            query = """
                SELECT 
                    h.date AS `Ngày`,
                    h.hàm_lượng AS `Hàm lượng (%%)`,
                    h.khối_lượng AS `Khối lượng (tấn)`,
                    p.price AS `Giá (VND/tấn)`,
                    (h.hàm_lượng / 100) * h.khối_lượng * p.price AS `Thành tiền (VND)`
                FROM 
                    hàm_lượng h
                JOIN 
                    price p ON h.date = p.day
                WHERE 
                    h.user_id = %s
                ORDER BY 
                    h.date DESC;
            """
            cursor.execute(query, (user_id,))
            transactions = cursor.fetchall()
            
            # Lấy thông tin người dùng
            user_query = "SELECT full_name, email FROM user WHERE user_id = %s"
            cursor.execute(user_query, (user_id,))
            user_info = cursor.fetchone()
    except pymysql.MySQLError as e:
        print(f"Lỗi cơ sở dữ liệu: {e}")
        transactions = []
        user_info = {}
    finally:
        if conn:
            conn.close()
    return render_template('customer_dashboard.html', transactions=transactions, user_info=user_info)

@app.route('/customer_dashboard', methods=['POST'])
def customer_monthly_total():
    if request.method == 'POST' and 'reset' in request.form:
        return customer_dashboard()
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']  # Lấy user_id từ session
    print(request.method)
    if request.method == 'POST':
        print(request.form.get('month'))
        month = int(request.form.get('month', datetime.now().month))  # Lấy tháng từ query params, mặc định là tháng hiện tại
        
        year = int(request.form.get('year', datetime.now().year))  # Lấy năm từ query params, mặc định là năm hiện tại

        try:
            conn = pymysql.connect(**db_config)
            with conn.cursor() as cursor:
                # Tính tổng tiền và lấy chi tiết giao dịch theo tháng
                query = """
                    SELECT 
                        h.date AS `Ngày`,
                        h.hàm_lượng AS `Hàm lượng (%%)`,
                        h.khối_lượng AS `Khối lượng (tấn)`,
                        p.price AS `Giá (VND/tấn)`,
                        (h.hàm_lượng / 100) * h.khối_lượng * p.price AS `Thành tiền (VND)`
                    FROM 
                        hàm_lượng h
                    JOIN 
                        price p ON h.date = p.day
                    WHERE 
                        h.user_id = %s
                        AND MONTH(h.date) = %s
                        AND YEAR(h.date) = %s
                    ORDER BY 
                        h.date DESC;
                """
                
                cursor.execute(query, (user_id, month, year))
            
                transactions = cursor.fetchall()
                

                # Tính tổng tiền
                total = sum(t['Thành tiền (VND)'] for t in transactions)
                user_query = "SELECT full_name, email FROM user WHERE user_id = %s"
                cursor.execute(user_query, (user_id,))
                user_info = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Lỗi cơ sở dữ liệu: {e}")
            transactions = []
            total = 0
        finally:
            if conn:
                conn.close()

    return render_template(
        'customer_dashboard.html',  # Vẫn sử dụng cùng file HTML
        transactions=transactions, 
        total=total, 
        month=month, 
        year=year,
        user_info=user_info
    )


    
@app.template_filter('format_price_vn')
def format_price_vn(price):
    if isinstance(price, (int, float)):
        # Định dạng giá trị thành chuỗi với phân cách hàng nghìn
        formatted_value = f"{price:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        return formatted_value
    return price
#--------------------------------------------------------------------------------------------------------------------------------

# Dashboard cho quản lý


@app.route('/manager_dashboard')
def manager_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # Lấy danh sách khách hàng
            user_query = """
                SELECT l.user_id, l.username, u.full_name, u.email, u.phone, u.rfid
                FROM login l
                INNER JOIN user u ON l.user_id = u.user_id
                WHERE l.role = 'customer'
            """
            cursor.execute(user_query)
            users = cursor.fetchall()

            # Lấy tất cả giao dịch
            transaction_query = """
                SELECT 
                    u.full_name AS user_name, h.date, h.hàm_lượng AS ham_luong, 
                    h.khối_lượng AS khoi_luong, p.price AS gia,
                    (h.khối_lượng * h.hàm_lượng / 100 * p.price) AS thanh_tien
                FROM hàm_lượng h
                JOIN user u ON h.user_id = u.user_id
                JOIN price p ON h.date = p.day
                ORDER BY h.date DESC
            """
            cursor.execute(transaction_query)
            transactions = cursor.fetchall()

    except pymysql.MySQLError as e:
        users, transactions = [], []
        print(f"Lỗi cơ sở dữ liệu: {e}")
    finally:
        if conn:
            conn.close()

    # Truyền dữ liệu vào giao diện
    return render_template('manager_dashboard.html', users=users, transactions=transactions)


@app.route('/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
            # Xóa trong bảng login trước
            login_query = "DELETE FROM login WHERE user_id = %s"
            cursor.execute(login_query, (user_id,))
            
            # Xóa trong bảng user sau
            user_query = "DELETE FROM user WHERE user_id = %s"
            cursor.execute(user_query, (user_id,))
            
            # Lưu thay đổi
            conn.commit()
        flash('Xóa người dùng thành công!', 'success')
    except pymysql.MySQLError as e:
        flash(f"Lỗi cơ sở dữ liệu: {e}", 'danger')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('manager_dashboard'))



@app.route('/view_transactions/<int:user_id>', methods=['GET'])
def view_transactions(user_id):
    # Truy vấn danh sách giao dịch của người dùng
    transactions = get_user_transactions(user_id)  # Hàm lấy giao dịch của người dùng
    
    # Truyền dữ liệu vào template
    return render_template('view_transactions.html', transactions=transactions)

#-------------------------------------------------------------------------------------------------------------------------------

# Đăng xuất
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Đăng xuất thành công!', 'success')
    return redirect(url_for('login'))
#--------------------------------------------------------------------------------------------------------------------------------

# With esp

@app.route('/api/data', methods=['POST'])
def receive_data():

    try:
        # Nhận dữ liệu JSON từ ESP32
        data = request.json
        print(data)
        rfid = data.get('rfid')
        
        value = data.get('value')
        timestamp = datetime.now().date()  # Lấy chỉ phần ngày

        if not rfid or not value:
            return jsonify({"error": "RFID và giá trị không được bỏ trống"}), 400

        # Lưu vào cơ sở dữ liệu
        conn = pymysql.connect(**db_config)
        with conn.cursor() as cursor:
        
           
            # Kiểm tra RFID có tồn tại trong bảng `user`
            cursor.execute("SELECT user_id FROM user WHERE RFID = %s", (rfid))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "RFID không hợp lệ"}), 404

            user_id = user.get('user_id')
            print(user_id)
            # Thêm dữ liệu vào bảng `hàm_lượng`
            cursor.execute("""
                INSERT INTO hàm_lượng (user_id, date, khối_lượng, hàm_lượng) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, timestamp, round(random.uniform(0.1, 10.0), 1), value.get('hàm_lượng')))

            conn.commit()
            cursor.close()
            conn.close()
        
            return jsonify({"message": "Dữ liệu đã được lưu thành công"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
    price = get_rubber_price()
    if price:
        update_price_in_db(price)
    else:
        print("Không thể lấy giá cao su từ trang web.")