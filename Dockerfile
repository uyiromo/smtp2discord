FROM python:3.13-alpine

ENV SMTP_PORT=25

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY discord.json .
COPY smtpd.py     .

# Command to run the application
CMD ["python", "smtpd.py"]
