# Published image for the shipped GUI (gui/v1). Local development stays
# ./run_gui.sh on the machine that has the source tree.
FROM python:3.13-slim

LABEL org.opencontainers.image.source=https://github.com/ajmscherer/finproj
LABEL org.opencontainers.image.description="finproj local Monte Carlo portfolio projections"
LABEL org.opencontainers.image.licenses=AGPL-3.0-only

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements-gui.txt .
RUN pip install --no-cache-dir -r requirements-gui.txt

COPY . .

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "gui/v1/app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true"]
