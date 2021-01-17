FROM python:2.7

ENV TVH_SERVER=127.0.0.1

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY tvh ./tvh
COPY server.py .

CMD [ "python", "./server.py" ]