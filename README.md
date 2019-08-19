# estuary-deployer-service
Estuary docker deployer service which will run your docker containers and/or your tests.  

## Build & Coverage
[![Build Status](https://travis-ci.org/dinuta/estuary-deployer-service.svg?branch=master)](https://travis-ci.org/dinuta/estuary-deployer)
[![Coverage Status](https://coveralls.io/repos/github/dinuta/estuary-deployer/badge.svg?branch=master)](https://coveralls.io/github/dinuta/estuary-deployer?branch=master)
## Docker Hub
[![](https://images.microbadger.com/badges/image/dinutac/estuary-deployer.svg)](https://microbadger.com/images/dinutac/estuary-deployer "Get your own image badge on microbadger.com") [![](https://images.microbadger.com/badges/version/dinutac/estuary-deployer.svg)](https://microbadger.com/images/dinutac/estuary-deployer "Get your own version badge on microbadger.com") ![](https://img.shields.io/docker/pulls/dinutac/estuary-deployer.svg)

## Api docs 
https://app.swaggerhub.com/apis/dinuta/estuary-deployer/1.0.0

## Postman collection
https://documenter.getpostman.com/view/2360061/SVYjUNCG


## Service run
##### Using docker compose ###
    docker-compose up
    
##### Using docker run ###
    On Linux/Mac:
    
    docker run \ 
    -e MAX_DEPLOY_MEMORY=80 \
    -p 8080:8080
    -v $PWD/inputs/templates:/data \ 
    -v $PWD/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    dinutac/estuary-deployer:<tag>
    
    On Windows:
            
    docker run \ 
    -e MAX_DEPLOY_MEMORY=80 \
    -p 8080:8080
    -v %cd%/inputs/templates:/data \ 
    -v %cd%/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    dinutac/estuary-deployer:<tag>
