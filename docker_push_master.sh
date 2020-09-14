#!/bin/bash

echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

#centos
docker build -t estuaryoss/deployer-centos:latest -f Dockerfiles/Dockerfile_centos .
docker push estuaryoss/deployer-centos:latest

#for alpine clean everything
git reset --hard && git clean -dfx
git checkout "${TRAVIS_BRANCH}"

#alpine
docker build . -t estuaryoss/deployer:latest
docker push estuaryoss/deployer:latest
