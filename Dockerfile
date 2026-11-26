FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY contracts/ /build/contracts/
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm AS python-build
WORKDIR /build
COPY requirements.lock.txt pyproject.toml ./
COPY specguard/ specguard/
RUN python -m pip install --no-cache-dir -c requirements.lock.txt setuptools wheel && \
    python -m pip wheel --no-cache-dir --no-build-isolation -c requirements.lock.txt -w /wheels .

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SPECGUARD_LIVE=0 PORT=8080
RUN groupadd --gid 10001 specguard && useradd --uid 10001 --gid 10001 --create-home specguard
COPY --from=python-build /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels specguard-ai && rm -r /wheels
COPY --from=frontend /build/frontend/dist/ frontend/dist/
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec python -m uvicorn specguard.cloud:app --host 0.0.0.0 --port \"$PORT\" --workers 1 --no-access-log --no-proxy-headers"]
