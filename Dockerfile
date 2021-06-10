# FastAPI optimized
# https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker
# poetry export -f requirements.txt --output requirements.txt --without-hashes
FROM python:3.9
ENV APP_HOME /app
WORKDIR ${APP_HOME}
COPY requirements.txt ./
RUN pip install --trusted-host pypi.python.org -r requirements.txt
COPY . ./
CMD exec gunicorn --config python:src.gunicorn_config --bind :$PORT src.main:app
