FROM python:3.9-slim

# Instalar Chrome, ChromeDriver e ALL dependências de display
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-browser \
    chromium-driver \
    ca-certificates \
    fonts-dejavu-core \
    fonts-liberation \
    libappindicator1 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libc6 \
    libcairo2 \
    libcurl4 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libfreetype6 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libgtk-3-common \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    nspr \
    nss \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Definir working directory
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Expor porta
EXPOSE 8000

# Rodar app
CMD ["python", "app.py"]