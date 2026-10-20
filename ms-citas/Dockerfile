FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home app && chown app /app
COPY --chown=app:app app ./app
USER app
EXPOSE 3002
CMD ["sh", "-c", "python -m app.db && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 3002"]
