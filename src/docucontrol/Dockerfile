FROM python:3.11-slim

WORKDIR /app

# System-Pakete: CUPS-Headers (pycups), Fonts (PDF), tzdata
RUN apt-get update && apt-get install -y \
    libcups2-dev \
    gcc \
    fonts-dejavu \
    fonts-liberation \
    tzdata \
    sudo \
    dosfstools \
    poppler-utils \
    iproute2 \
    network-manager \
    cifs-utils \
    util-linux-extra \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Berlin

# Hardcodierte Pfade im App-Code zeigen auf /home/docucontrol/docupi/
# Symlink damit DB, Configs und Logs am richtigen Ort landen
RUN mkdir -p /home/docucontrol && ln -s /app /home/docucontrol/docupi

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port 5000: Flask Web | Port 9100: TCP-Empfang
EXPOSE 5000 9100

CMD ["python3", "app.py"]
