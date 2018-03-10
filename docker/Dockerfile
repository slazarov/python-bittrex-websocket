# Use an official Python runtime as a parent image
FROM python:3.6.3-alpine

RUN   apk update && apk add --no-cache --virtual .build-deps \
      g++ make libffi-dev openssl-dev git && \
      apk --update add nodejs && \
      pip install 'cython>=0.25' && \
      pip install git+https://github.com/slazarov/python-bittrex-websocket.git@ && \
      apk del .build-deps && \
      rm -rf /var/cache/apk/*

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Run app.py when the container launches
CMD ["python", "example.py"]
