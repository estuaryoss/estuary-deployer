#!/bin/bash

echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

#centos
docker build -t estuaryoss/deployer:"${TRAVIS_TAG}" -f Dockerfile .
docker push estuaryoss/deployer:"${TRAVIS_TAG}"