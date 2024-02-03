FROM python:3

LABEL org.opencontainers.image.source https://github.com/0x4d4d/tvheadend-exporter

ENV TVH_SERVER=127.0.0.1
ENV TVH_PORT=9981

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY tvh ./tvh
COPY server.py .

HEALTHCHECK --timeout=3s \
  CMD curl -f http://localhost:9429 || exit 1

CMD [ "python", "./server.py" ]