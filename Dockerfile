FROM python:3

LABEL org.opencontainers.image.source https://github.com/0x4d4d/tvheadend-exporter

ENV TVH_SERVER=127.0.0.1
ENV TVH_PORT=9981

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY tvh ./tvh
COPY server.py .

CMD [ "python", "./server.py" ]