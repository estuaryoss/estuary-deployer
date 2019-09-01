# Testing as a Service with Docker
## estuary-deployer
Estuary docker deployer service which will run your docker containers and/or your tests.  

## Build & Coverage
[![Build Status](https://travis-ci.org/dinuta/estuary-deployer.svg?branch=master)](https://travis-ci.org/dinuta/estuary-deployer)
[![Coverage Status](https://coveralls.io/repos/github/dinuta/estuary-deployer/badge.svg?branch=master)](https://coveralls.io/github/dinuta/estuary-deployer?branch=master)
## Docker Hub
[![](https://images.microbadger.com/badges/image/dinutac/estuary-deployer.svg)](https://microbadger.com/images/dinutac/estuary-deployer "Get your own image badge on microbadger.com") [![](https://images.microbadger.com/badges/version/dinutac/estuary-deployer.svg)](https://microbadger.com/images/dinutac/estuary-deployer "Get your own version badge on microbadger.com") ![](https://img.shields.io/docker/pulls/dinutac/estuary-deployer.svg)

## Api docs 
https://app.swaggerhub.com/apis/dinuta/estuary-deployer/1.0.0
https://app.swaggerhub.com/apis/dinuta/estuary-deployer/2.0.0

## Postman collection
https://documenter.getpostman.com/view/2360061/SVYjUNCG


## Service run
##### Using docker compose 
    docker-compose up
    
##### Using docker run - simple 
    On Linux/Mac:
    
    docker network create estuarydeployer_default
    docker run \ 
    -e MAX_DEPLOY_MEMORY=80 \
    -p 8080:8080
    -v $PWD/inputs/templates:/data \ 
    -v $PWD/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --net=estuarydeployer_default \
    dinutac/estuary-deployer:<tag>
    
    On Windows:
    
    docker network create estuarydeployer_default        
    docker run \ 
    -e MAX_DEPLOY_MEMORY=80 \
    -p 8080:8080
    -v %cd%/inputs/templates:/data \ 
    -v %cd%/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --net=estuarydeployer_default \
    dinutac/estuary-deployer:<tag>


##### Using docker run - eureka registration
To have all your deployer instances in a central location we use netflix eureka. This means your client will discover
all services used for your test and then spread the tests across all.  

Start Eureka server with docker:  

    docker run -p 8080:8080 netflixoss/eureka:1.3.1  

Start your containers by specifying the full hostname or ip of the host machine on where your deployer service resides.  

    On Linux/Mac:
    
    docker network create estuarydeployer_default
    docker run \
    -e MAX_DEPLOYMENTS=3 \ #optional->  how many deployments to be done. it is an option to deploy a fixed no of docker-compose envs
    -e MAX_DEPLOY_MEMORY=80 \ #optional-> how much % of memory to be used by deployer service
    -e EUREKA_SERVER=http://10.133.14.238:8080/eureka/v2 # optional
    -e APP_IP_PORT=10.133.14.238:8081 #optional, but mandatory if EUREKA_SERVER env var is used -> the app hostname/ip:port
    -e APP_APPEND_ID=SR #optional-> this id will be appended to the default app name on service registration. Useful for user mappings service- resources on a VM
    -p 8080:8080
    -v $PWD/inputs/templates:/data \
    -v $PWD/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --net=estuarydeployer_default
    dinutac/estuary-deployer:<tag>

    On Windows:
    docker network create estuarydeployer_default
    docker run \
    -e MAX_DEPLOYMENTS=3 \ #optional->  how many deployments to be done. it is an option to deploy a fixed no of docker-compose envs
    -e MAX_DEPLOY_MEMORY=80 \ #optional-> how much % of memory to be used by deployer service
    -e EUREKA_SERVER=http://10.133.14.238:8080/eureka/v2 # optional
    -e APP_IP_PORT=10.133.14.238:8081 #optional, but mandatory if EUREKA_SERVER env var is used -> the app hostname/ip:port
    -e APP_APPEND_ID=SR #optional-> this id will be appended to the default app name on service registration. Useful for user mappings service- resources on a VM
    -p 8080:8080
    -v %cd%/inputs/templates:/data \
    -v %cd%/inputs/variables:/variables \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --net=estuarydeployer_default
    dinutac/estuary-deployer:<tag>
