FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY service ./service
RUN python -m pip install --no-cache-dir '.[web]'

USER 65534
EXPOSE 8000
CMD ["uvicorn", "service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
