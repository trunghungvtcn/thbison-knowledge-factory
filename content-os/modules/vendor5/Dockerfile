FROM python:3.12-slim
RUN useradd -m -u 10001 appuser
WORKDIR /app
COPY vendor/wheelhouse /app/vendor/wheelhouse
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-index --find-links /app/vendor/wheelhouse -r requirements.txt || pip install --no-cache-dir -r requirements.txt
COPY . /app
RUN chown -R appuser:appuser /app
USER appuser
ENV APP_MODE=MOCK STAGING_ENABLED=false STAGING_WRITE_ENABLED=false ALLOW_PRODUCTION=false ALLOW_PUBLIC_EFFECTS=false
EXPOSE 8080
CMD ["python", "-m", "app.httpapi"]
