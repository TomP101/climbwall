FROM python:3.12-slim

# Ustaw katalog roboczy w kontenerze
WORKDIR /app

# Skopiuj wszystko do kontenera
COPY . /app

# Zainstaluj zależności (bez requirements.txt, żeby było mniej plików)
RUN pip install --no-cache-dir flask flask_sqlalchemy mysql-connector-python

# Aplikacja słucha na porcie 5000
EXPOSE 5000

# Komenda startowa
CMD ["python", "app.py"]
