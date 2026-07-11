# SafetyOps Copilot — API + worker image (Hugging Face Spaces compatible).
#
# Build:            docker build -t safetyops .
# Slim (no ML):     docker build --build-arg INSTALL_ML=false -t safetyops .
# Run:              docker run -p 7860:7860 --env-file .env safetyops
#
# The UI (apps/ui) is deployed separately (e.g. Streamlit Community Cloud).

FROM python:3.11-slim

WORKDIR /app

# libgl/libglib are needed by opencv (pulled in by ultralytics).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/

ARG INSTALL_ML=true
RUN pip install --no-cache-dir -r requirements/api.txt -r requirements/worker.txt \
    && if [ "$INSTALL_ML" = "true" ]; then \
        # CPU-only torch keeps the image several GB smaller than the CUDA default.
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
        && pip install --no-cache-dir -r requirements/ml.txt; \
    fi

COPY . .

# Non-root user (required by Hugging Face Spaces); needs write access for
# uploads, artifacts, and downloaded models.
RUN useradd -m -u 1000 appuser \
    && mkdir -p data/uploads artifacts models/nlp models/vision \
    && chown -R appuser:appuser /app
USER appuser

ENV SAFETYOPS_DEPLOY_MODE=cloud \
    PORT=7860

EXPOSE 7860

CMD ["sh", "scripts/start_cloud.sh"]
