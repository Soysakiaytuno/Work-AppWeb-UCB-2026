FROM python:3.12-slim
RUN pip3 install flask
COPY config/ /site_config/
EXPOSE 5000
CMD ["python3", "/site_config/app.py"]