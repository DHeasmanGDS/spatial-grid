FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Geopandas / shapely / pyproj all ship binary wheels with their native libs
# bundled (GDAL via pyogrio, GEOS via shapely, PROJ via pyproj) so we don't
# need apt-get install libgdal-dev / libgeos-dev / libproj-dev.

COPY pyproject.toml README.md ./
COPY spatial_grid ./spatial_grid
COPY .streamlit ./.streamlit

# Install the package + UI extras. -e isn't needed in a container.
RUN pip install --upgrade pip && pip install ".[ui]"

EXPOSE 8501

# Streamlit + Cloudflare Tunnel need CORS/XSRF off because the tunnel
# rewrites the Host header (the WebSocket handshake fails XSRF otherwise).
# Headless silences the "open browser" prompt.
CMD ["streamlit", "run", "spatial_grid/ui_app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--browser.gatherUsageStats=false"]
