# Chọn image Python chính thức làm base image
FROM python:3.9-slim

WORKDIR /app

# Sao chép tệp requirements.txt vào container
COPY app/requirements.txt /app/

# Cài đặt các phụ thuộc hệ thống cần thiết
RUN apt-get update && apt-get install -y default-libmysqlclient-dev




RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng vào container
COPY app /app/

# Sao chép file init.sql vào thư mục db trong container (nếu có)
COPY db/init.sql /db/init.sql

# Mở cổng ứng dụng (ví dụ: 5000 cho Flask)
EXPOSE 5000

# Lệnh chạy ứng dụng Flask
CMD ["python", "app/app.py"]


