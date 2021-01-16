FROM python:2.7

WORKDIR /code

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY tvh ./tvh
COPY server.py .

CMD [ "python", "./server.py" ]