# --- Backend build (FastAPI) ---
FROM python:3.10-slim as backend
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
COPY backend .

# --- Frontend build (React) ---
    FROM node:18-alpine as frontend
    WORKDIR /app/frontend
    COPY frontend/package*.json ./
    RUN npm install --legacy-peer-deps
    COPY frontend .
    RUN NODE_OPTIONS=--openssl-legacy-provider npm run build
# --- Final image ---
FROM python:3.10-slim as final
WORKDIR /app

# Copy backend
COPY --from=backend /app/backend /app/backend
# Copy frontend build
COPY --from=frontend /app/frontend/build /app/frontend/build

# Install backend dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt
# Download spaCy model in the final image
RUN python -m spacy download en_core_web_sm

# Environment for FastAPI
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Entrypoint: run backend (serving API and static frontend)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
