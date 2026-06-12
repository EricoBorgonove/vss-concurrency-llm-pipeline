ARG BASE_PLATFORM=linux/amd64
FROM --platform=$BASE_PLATFORM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        software-properties-common \
        gnupg \
    && add-apt-repository -y ppa:esbmc/esbmc \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        afl++ \
        clang \
        esbmc \
        gcc \
        g++ \
        libclang-rt-17-dev \
        libclang-rt-18-dev \
        python3 \
        python3-pip \
        python3-venv \
        time \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

COPY . /workspace

CMD ["python3", "run_pipeline.py"]
