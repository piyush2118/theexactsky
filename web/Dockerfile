# One image: the engine, its vendored data, resvg, and uvicorn.
#
# resvg is built from source rather than pulled from a release tarball so that
# the container is not tied to a GitHub asset that can move. The version is
# pinned, because a rasteriser that changes underneath you changes every card.

FROM rust:1.83-slim-bookworm AS resvg
ARG RESVG_VERSION=0.45.1
RUN cargo install resvg --version ${RESVG_VERSION} --locked

FROM python:3.12-slim-bookworm

COPY --from=resvg /usr/local/cargo/bin/resvg /usr/local/bin/resvg
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /srv

# The engine and its data first: they change far less often than the templates,
# and the ephemeris layer is 90 MB that should not be rebuilt on a CSS edit.
COPY engine/pyproject.toml engine/uv.lock /srv/engine/
COPY engine/skurious /srv/engine/skurious
COPY engine/data /srv/engine/data

COPY web/pyproject.toml web/uv.lock /srv/web/
RUN cd /srv/web && uv sync --frozen --no-dev

COPY web/app /srv/web/app
COPY web/templates /srv/web/templates
COPY web/static /srv/web/static

ENV SKURIOUS_CACHE=/var/lib/skurious/cards \
    SKURIOUS_DB=/var/lib/skurious/skurious.sqlite \
    PATH="/srv/web/.venv/bin:$PATH"
RUN mkdir -p /var/lib/skurious/cards

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=4).status==200 else 1)"

WORKDIR /srv/web
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
