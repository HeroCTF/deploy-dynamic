FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir -r requirements.txt && \
    rm requirements.txt

EXPOSE 5000
CMD ["python3", "/app/app.py"]