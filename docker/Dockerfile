# syntax=docker/dockerfile:1
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    AUTOMATION_ENV=dev

WORKDIR /opt/automation

RUN pip install --no-cache-dir poetry==1.8.5

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-ansi

# Playwright's own installer pulls the OS packages each browser engine needs
# (--with-deps) — python:3.13-slim has none of them preinstalled, unlike the
# mcr.microsoft.com/playwright images (which only ship Python 3.10 and can't
# satisfy this project's ^3.13 requirement).
RUN python -m playwright install --with-deps chromium firefox webkit

COPY . .

RUN mkdir -p artifacts/screenshots artifacts/videos artifacts/traces artifacts/har \
    reports/allure-results reports/allure-report logs

ENTRYPOINT ["python", "-m", "pytest"]
CMD ["tests/smoke", "-v", "--alluredir=reports/allure-results"]
