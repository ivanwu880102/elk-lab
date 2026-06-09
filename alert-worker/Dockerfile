FROM python:3.12-slim

WORKDIR /app

RUN pip install requests

COPY alert_worker.py /app/alert_worker.py

CMD ["python", "alert_worker.py"]