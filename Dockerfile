FROM python:3.13-alpine

WORKDIR /app/

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir -r requirements.txt && \
    sed -i 's/from jinja2 import/from markupsafe import/g' /usr/local/lib/python3.13/site-packages/flask_recaptcha.py

EXPOSE 5000
CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "--threads=8", "run:app"]