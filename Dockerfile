FROM ubuntu:22.04
RUN apt-get update && apt-get install -y nano 
RUN apt-get install -y python3 && rm -rf /var/lib/apt/lists/*
COPY config/ /site_config/
CMD [ "python3", "main.py" ]