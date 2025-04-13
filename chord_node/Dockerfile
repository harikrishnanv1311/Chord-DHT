FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y \
    python3 \
    python3-pip \
    net-tools \
    iputils-ping \
    iproute2 \
    curl \
    wget \
    dnsutils \
    vim \
    procps \
    lsof && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip3 install flask requests debugpy flask-cors

CMD ["python3", "-u", "api.py"]
