#!/bin/bash

echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

#centos
docker build -t dinutac/estuary-deployer-centos:latest -f Dockerfile_centos .
docker push dinutac/estuary-deployer-centos:latest

#for alpine clean everything
git reset --hard && git clean -dfx
git checkout "${TRAVIS_BRANCH}"

#alpine
docker build . -t dinutac/estuary-deployer:latest
docker push dinutac/estuary-deployer:latest
