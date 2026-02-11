# 1. Base Image
FROM python:3.10-slim

# 2. System Layer (The HEAVIEST part - stays cached forever)
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

# 3. Setup workspace
WORKDIR /app

# 4. Dependency Layer (Only rebuilds if you change requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Code Layer (Changes frequently - built in < 1 second)
COPY songs.txt .
COPY main.py .
COPY config.py .
COPY logger.py .
COPY file_processor.py .
COPY metadata_utils.py .
COPY downloader.py .
COPY lyrics_engine.py .

# 6. Create storage
RUN mkdir -p /app/downloads

CMD ["python", "main.py"]
