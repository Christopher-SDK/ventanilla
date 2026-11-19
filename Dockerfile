FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH" VENTANILLA_RAIZ=/app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY corpus ./corpus
COPY datos ./datos
COPY grabaciones ./grabaciones
RUN uv sync --frozen --no-dev && useradd --create-home --uid 10001 ventanilla && chown -R ventanilla /app/grabaciones
USER ventanilla
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/salud')"
CMD ["uvicorn", "ventanilla.adaptadores.api:app_desde_entorno", "--factory", "--host", "0.0.0.0", "--port", "8000"]
