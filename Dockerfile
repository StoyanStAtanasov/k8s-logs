FROM python:3.11-slim

WORKDIR /app

# copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app sources
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 80

# minimal command to run a FastAPI app defined in main.py as `app`
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]