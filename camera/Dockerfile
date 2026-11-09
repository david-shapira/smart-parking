FROM python:3.12-alpine

WORKDIR /app
COPY camera.py .

# -u = unbuffered output, so logs show up immediately in `docker compose logs`
CMD ["python", "-u", "camera.py"]
