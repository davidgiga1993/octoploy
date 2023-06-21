FROM python:3.9-slim-buster

WORKDIR /app
COPY requirements-docker.txt .
COPY dist/octoploy*.whl .
RUN pip install *.whl && \
	pip install -r requirements-docker.txt && \
	rm *.whl


ENV PYTHONPATH "${PYTHONPATH}:/octoploy"
ENTRYPOINT ["python", "-m", "main"]