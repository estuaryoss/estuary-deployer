#!/bin/bash

echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

#compile
pip3 install -r requirements.txt
pyinstaller --onefile --clean --add-data="rest/api/views/swaggerui/**:rest/api/views/swaggerui/" main.py

#centos
docker build -t estuaryoss/deployer:latest -f Dockerfile .
docker push estuaryoss/deployer:latest