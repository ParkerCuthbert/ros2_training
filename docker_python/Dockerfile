# Use the official Ubuntu 22.04 as a base image
FROM ubuntu:22.04

# Update the package list and install Python 3
RUN apt-get update && apt-get install -y python3

# Copy the hello.py script to the container
COPY hello.py /hello.py

# Set the entry point to run the Python script
ENTRYPOINT ["python3", "/hello.py"]
