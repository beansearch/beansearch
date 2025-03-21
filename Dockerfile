# FROM node:20
# WORKDIR /build
# COPY static/index.html index.html
# RUN npm install -D tailwindcss @tailwindcss/cli
# RUN npx @tailwindcss/cli -o ./tailwind.css -m

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY 3bs.db ./
COPY static static
# COPY --from=0 /build/tailwind.css ./static/

WORKDIR /app
EXPOSE 5000
CMD ["gunicorn", "--access-logfile", "-", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
