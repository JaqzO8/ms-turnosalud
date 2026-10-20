FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY app ./app
EXPOSE 3003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3003"]
