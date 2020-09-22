#!/bin/bash

echo "$DOCKERHUB_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin

#centos
docker build -t dinutac/estuary-deployer-centos:"${TRAVIS_TAG}" -f Dockerfile_centos .
docker push dinutac/estuary-deployer-centos:"${TRAVIS_TAG}"

#for alpine clean everything
git reset --hard && git clean -dfx
git checkout tags/"${TRAVIS_TAG}" -b "${TRAVIS_TAG}"

#alpine
docker build . -t dinutac/estuary-deployer:"${TRAVIS_TAG}"
docker push dinutac/estuary-deployer:"${TRAVIS_TAG}"
