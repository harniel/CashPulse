# Multi-stage: `dev` runs manage.py runserver against a live-mounted
# volume (docker-compose.yml's default target); `prod` bakes the code in
# and runs gunicorn — Section 21's "gunicorn in a prod-target stage".

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS dev

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
# Shell form (not exec form) so $PORT actually expands — Railway/Render
# inject it at runtime and expect the container to bind to it; falls
# back to 8000 for `docker compose up` locally, which doesn't set it.
# Migrations run here rather than as a separate release-phase step:
# fine for a single-instance portfolio deploy (no replicas racing to
# migrate at once), the tradeoff BLUEPRINT.md §23 already calls out.
CMD python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}
