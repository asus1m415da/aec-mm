# Imagen base de Python estable
FROM python:3.10-slim

# Evitar archivos temporales y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos las dependencias necesarias directamente
# ⚠️ AQUÍ FALTABAN LAS LIBRERÍAS NUEVAS
RUN pip install --no-cache-dir \
    discord.py \
    python-dotenv \
    groq \
    flask \
    requests \
    fake-useragent \
    pymongo[srv]

# Copiamos el código de tu bot al contenedor
COPY . .

# Comando para arrancar el bot
CMD ["python", "main.py"]
