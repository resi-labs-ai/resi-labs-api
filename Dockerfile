FROM python:3.12

# Install system dependencies including Rust
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY s3_storage_api/ ./s3_storage_api/

# Use ARG for build-time variables
ARG S3_BUCKET_DEFAULT=1000-resilabs-caleb-dev-bittensor-sn46-datacollection
ARG S3_REGION_DEFAULT=us-east-2
ARG NET_UID_DEFAULT=46

# Set ENV variables with ARG defaults
ENV PORT=8000
ENV S3_BUCKET=${S3_BUCKET_DEFAULT}
ENV S3_REGION=${S3_REGION_DEFAULT}
ENV NET_UID=${NET_UID_DEFAULT}
ENV BT_NETWORK=finney

CMD ["uvicorn", "s3_storage_api.server:app", "--host", "0.0.0.0", "--port", "8000"]
