FROM python:3.9-slim-buster

WORKDIR /app
COPY dist/octoploy*.whl .
RUN apt update && \
    apt install -y curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl && \
    apt clean

RUN pip install *.whl && \
	rm *.whl

ENTRYPOINT ["/usr/local/bin/octoploy"]