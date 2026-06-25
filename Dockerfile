# Use a slim Python 3.11 image (3.12/3.13 can have issues with latex2sympy2)
FROM python:3.11-slim

# Install system dependencies (Tesseract for OCR, build tools)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY backend/ .

# Expose the API port
EXPOSE 8000
