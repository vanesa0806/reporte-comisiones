# Usar una imagen base de Python
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY app/ .

# Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el script
CMD ["python", "main.py"]
