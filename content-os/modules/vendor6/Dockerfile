FROM python:3.11-slim
RUN useradd -m -u 10001 appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY contracts ./contracts
COPY CONTRACT_SHA256.txt COMPONENT_MATRIX.json STAGING_ACCESS_MANIFEST.json ./
USER appuser
ENV PYTHONPATH=/app/src
CMD ["python", "-c", "from thbison_v6.harness.lab import Lab; print(Lab().contract_digest)"]
