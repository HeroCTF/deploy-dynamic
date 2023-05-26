FROM python:3.9

WORKDIR /usr/srv/app

COPY ./app/ ./app/
COPY app.py .
COPY requirements.txt .
COPY config.json .

RUN python3 -m pip install \
    --no-cache-dir -r requirements.txt

CMD ["python3", "app.py"]