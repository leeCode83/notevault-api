# Gunakan image Python resmi yang ringan (slim)
FROM python:3.11-slim

# Mencegah Python menulis file .pyc ke disk
ENV PYTHONDONTWRITEBYTECODE=1
# Memastikan output Python tidak di-buffer agar log langsung muncul
ENV PYTHONUNBUFFERED=1

# Set working directory di dalam container
WORKDIR /app

# Install system dependencies yang mungkin dibutuhkan oleh paket Python (opsional tapi disarankan)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements terlebih dahulu untuk memanfaatkan Docker cache build
COPY requirements.txt .

# Install dependencies Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh source code project ke dalam container
COPY . .

# Expose port yang digunakan oleh FastAPI
EXPOSE 8000

# Command untuk menjalankan aplikasi menggunakan uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
