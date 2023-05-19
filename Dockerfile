FROM python:3.10-slim-buster

WORKDIR /app

COPY Pipfile Pipfile.lock ./

RUN pip install --no-cache-dir pipenv \
    && pipenv install --system --deploy --ignore-pipfile

COPY . .
COPY application_default_credentials.json $HOME/.config/gcloud/
ENV GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
