# Use the official Python 3.12 image as the base image
FROM python:3.11.12-slim

RUN pip install --upgrade pip setuptools
RUN apt-get update

RUN apt-get install -y expat
# Set the working directory in the container to /app
WORKDIR /app

# Copy the Python script into the container at /app
COPY requirements.txt .
COPY . .

RUN chmod +x /app/noachdm/cli.py
# Install the required Python packages specified in a requirements.txt file
# If you don't have a requirements.txt, you'll need to create one with the necessary packages
RUN pip install -r requirements.txt --no-cache-dir

# Command to run the script when the container starts
ENTRYPOINT ["python", "noachdm/cli.py"]

LABEL org.opencontainers.image.source=https://github.com/noa-beyond/eoProcessors/
LABEL org.opencontainers.image.description="National Observatory of Athens - Change Detection Mapping Processor"
LABEL org.opencontainers.image.licenses="GNU Affero General Public License v3.0"