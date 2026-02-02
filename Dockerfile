# Imagen base de Python estable
FROM python:3.10-slim

# Evitar archivos temporales y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos las dependencias necesarias directamente
# Esto evita que necesites un archivo requirements.txt por separado
RUN pip install --no-cache-dir \
    discord.py \
    python-dotenv \
    groq \
    flask

# Copiamos el código de tu bot al contenedor
COPY . .

# Comando para arrancar el bot
# RECUERDA: Cambia "main.py" por el nombre real de tu archivo de confesiones
CMD ["python", "main.py"]
