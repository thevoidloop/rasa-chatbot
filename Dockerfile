# Dockerfile para Rasa Chatbot en Español
FROM rasa/rasa:3.6.19-full

# Cambiar a usuario root para instalar dependencias adicionales
USER root

# Instalar dependencias del sistema necesarias para PostgreSQL
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Actualizar pip para evitar warnings
RUN pip install --upgrade pip

# Instalar dependencias adicionales de Python
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.7 \
    requests==2.31.0 \
    python-dotenv==1.0.0

# Crear directorio de trabajo
WORKDIR /app

# Crear directorio models con permisos correctos
RUN mkdir -p /app/models && chmod 777 /app/models

# Copiar archivo de requirements primero (para cache de Docker)
COPY requirements.txt* ./

# Instalar requirements adicionales si existen
RUN if [ -f requirements.txt ]; then \
    pip install --no-cache-dir -r requirements.txt --no-deps || \
    pip install --no-cache-dir -r requirements.txt; \
    fi

# Copiar archivos de configuración de Rasa
COPY config.yml ./
COPY domain.yml ./
COPY endpoints.yml ./
COPY credentials.yml ./

# Copiar datos de entrenamiento
COPY data/ ./data/

# Cambiar permisos y propiedad de archivos
RUN chown -R 1001:1001 /app
RUN chmod -R 755 /app

# Cambiar a usuario no-root para seguridad
USER 1001

# Puerto por defecto de Rasa
EXPOSE 5005

# Comando por defecto
CMD ["run", "--enable-api", "--cors", "*", "--debug"]