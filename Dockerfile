FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends g++ libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN bash scripts/build.sh && python -m pytest -q
CMD ["python", "-m", "edgevision", "--source", "artifacts/synthetic.avi", "--output", "artifacts/annotated.avi", "--metrics", "artifacts/metrics.json"]
