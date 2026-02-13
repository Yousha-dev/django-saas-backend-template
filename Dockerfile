# Use an official Python runtime as a parent image
FROM python:3.12

# Set the working directory in the container
WORKDIR /src

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    build-essential \
    wget \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
#COPY requirements.txt /src/
#RUN pip install --upgrade pip && pip install -r requirements.txt

# Accept build arguments and set environment variables
ARG SECRET_KEY
ENV SECRET_KEY=${SECRET_KEY}

ARG DEBUG
ENV DEBUG=${DEBUG}

ARG DB_NAME
ENV DB_NAME=${DB_NAME}

ARG DB_USER
ENV DB_USER=${DB_USER}

ARG DB_PASSWORD
ENV DB_PASSWORD=${DB_PASSWORD}

ARG DB_HOST
ENV DB_HOST=${DB_HOST}

ARG DB_PORT_NUMBER
ENV DB_PORT_NUMBER=${DB_PORT_NUMBER}

ARG REDIS_HOST
ENV REDIS_HOST=${REDIS_HOST}

ARG REDIS_PORT_NUMBER
ENV REDIS_PORT_NUMBER=${REDIS_PORT_NUMBER}

ARG REDIS_PASSWORD
ENV REDIS_PASSWORD=${REDIS_PASSWORD}

ARG RABBITMQ_HOST
ENV RABBITMQ_HOST=${RABBITMQ_HOST}

ARG RABBITMQ_PORT_NUMBER
ENV RABBITMQ_PORT_NUMBER=${RABBITMQ_PORT_NUMBER}

ARG RABBITMQ_USER
ENV RABBITMQ_USER=${RABBITMQ_USER}

ARG RABBITMQ_PASSWORD
ENV RABBITMQ_PASSWORD=${RABBITMQ_PASSWORD}

# Copy the entrypoint script first and set execute permissions
COPY entrypoint.sh /src/entrypoint.sh
RUN chmod +x /src/entrypoint.sh

# Copy the source code into the container
COPY src/ /src/

# Create directories for AI models and logs
RUN mkdir -p /src/logs

# Expose the application port
EXPOSE 8000

# Define the entrypoint
ENTRYPOINT ["./entrypoint.sh"]