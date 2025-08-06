# Use the official Python 3.12 image as the base image
FROM python:3.11.10-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    libexpat1 \
    libexpat1-dev \
    expat \
    && ldconfig

WORKDIR /app
COPY requirements.txt .
COPY . .

ENV LD_LIBRARY_PATH="/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

ENV CREODIAS_S3_ACCESS_KEY=NONE
ENV CREODIAS_S3_SECRET_KEY=NONE
ENV CREODIAS_REGION=WAW4-1
ENV CREODIAS_ENDPOINT=https://s3.waw4-1.cloudferro.com
ENV CREODIAS_S3_BUCKET_PRODUCT_OUTPUT=noa
ENV CREODIAS_S3_BUCKET_STAC=stac

RUN chmod +x /app/noastacingest/cli.py
# Install the required Python packages specified in a requirements.txt file
# If you don't have a requirements.txt, you'll need to create one with the necessary packages
RUN pip install --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Create a default Products download dir, even if not using it
RUN mkdir -p /mnt/data/poc/

# Command to run the script when the container starts
ENTRYPOINT ["python", "noastacingest/cli.py"]

LABEL org.opencontainers.image.source=https://github.com/noa-beyond/eoProcessors/
LABEL org.opencontainers.image.description="National Observatory of Athens - EO Data to STAC"
LABEL org.opencontainers.image.licenses="GNU Affero General Public License v3.0"