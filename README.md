<h1 align="center"><img src="./docs/images/banner_estuary.png" alt="Testing as a service with Docker"></h1>  

<meta name="google-site-verification" content="eI9kw0_EDymH5_kjr66RoT3PiK5MU8QpfkXazrGlfgE" />

Support project: <a href="https://paypal.me/catalindinuta?locale.x=en_US"><img src="https://pbs.twimg.com/profile_images/1145724063106519040/b1L98qh9_400x400.jpg" height="40" width="40" align="center"></a> 

# Testing as a Service
## Estuary deployer
Estuary docker deployer service which will run your containers and/or your tests.   
Starting with version [2.0.0](https://github.com/dinuta/estuary-deployer/releases/tag/2.0.0) the estuary-deployer service can run your tests using the [estuary-testrunner](https://github.com/dinuta/estuary-testrunner) service. Check-out the wiki !  

## Coverage & code quality
[![Coverage Status](https://coveralls.io/repos/github/dinuta/estuary-deployer/badge.svg?branch=master)](https://coveralls.io/github/dinuta/estuary-deployer?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/fd41fd77c2594a1f8211a5c1e8926117)](https://www.codacy.com/manual/dinuta/estuary-deployer?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=dinuta/estuary-deployer&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/415605917fdf321fcd83/maintainability)](https://codeclimate.com/github/dinuta/estuary-deployer/maintainability)

## Linux status
[![Build Status](https://travis-ci.org/dinuta/estuary-deployer.svg?branch=master)](https://travis-ci.org/dinuta/estuary-deployer)

## Docker Hub
[alpine](https://hub.docker.com/r/dinutac/estuary-deployer)  ![](https://img.shields.io/docker/pulls/dinutac/estuary-deployer.svg)  
[centos](https://hub.docker.com/r/dinutac/estuary-deployer-centos)  ![](https://img.shields.io/docker/pulls/dinutac/estuary-deployer-centos.svg)

## Api docs 
[4.0.1 docker](https://app.swaggerhub.com/apis/dinuta/estuary-deployer/4.0.1)  
[4.0.1 kubectl](https://app.swaggerhub.com/apis/dinuta/estuary-deployer/4.0.1-kubectl)  

## Postman collection 
[Docker](https://documenter.getpostman.com/view/2360061/SVYjUNCG)  
[Kubernetes](https://documenter.getpostman.com/view/2360061/SW15zGn2)

## Wiki
[Wiki](https://github.com/dinuta/estuary-deployer/wiki)  

## Use cases
-  Debug accelerator. No more logs attached to Jira. QAs can push the related bug-ish image to registry. Then in a docker compose QA can deploy "the bug" on a developer's machine or on dedicated debug machine (security reason due to docker sock mounting). The dev will have all he needs
-  Testing as a service. A complete enevironment SUT/BD/Automation Framework can be deployed and tested
-  Bring up Docker containers remotely through HTTP
-  Templating with Jinja2

## Service run
### Docker compose
    docker-compose up
    
### Docker run - simple
   
    docker network create estuarydeployer_default
    docker run -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock --net=estuarydeployer_default \
    dinutac/estuary-deployer:<tag>
    
    Jinja2 templating can be done, just add:
    Windows:
    -v %cd%/inputs/templates:/data \ 
    -v %cd%/inputs/variables:/variables \
    
    Linux:
    -v $PWD/inputs/templates:/data \ 
    -v $PWD/inputs/variables:/variables \

### Eureka registration
To have all your deployer instances in a central location we use netflix eureka. This means your client will discover
all services used for your test and then spread the tests across all.  

Start Eureka server with docker:  

    docker run -p 8080:8080 netflixoss/eureka:1.3.1  
    or
    docker run -p 8080:8080 dinutac/netflixoss-eureka:1.9.21

Start your containers by specifying the full hostname or ip of the host machine on where your deployer service resides.  
    
    docker network create estuarydeployer_default
    docker run params:
    Optional:
            -e MAX_DEPLOYMENTS=3 ->  how many deployments to be done. it is an option to deploy a fixed no of docker-compose envs(docker only)
            -e EUREKA_SERVER="http://10.13.14.28:8080/eureka/v2" -> eureka server
            -e APP_IP_PORT="10.13.14.28:8081" -> the app hostname/ip:port. Mandatory if EUREKA_SERVER is used
            -e APP_APPEND_ID="lab" -> id will be appended to the default app name on service registration. Useful for user mappings service-resources on a VM
            -e FLUENTD_IP_PORT="10.13.14.28:24224" -> fluentd __enrich_message collector agent target ip:port
            -e ENV_EXPIRE_IN=1440 -> how long it will take before the env will be deleted. Default is 1440 min.
    Mandatory:
        -p 8081:8080 -> port fwd from docker 8080 to host 8081
        -v /var/run/docker.sock:/var/run/docker.sock -> docker sock mount
        --net=estuarydeployer_default -> bind to this net prior created

    dinutac/estuary-deployer:latest


    
    Jinja2 templating can be done, just add:
    Windows:
    -v %cd%/inputs/templates:/data \ 
    -v %cd%/inputs/variables:/variables \
    
    Linux:
    -v $PWD/inputs/templates:/data \ 
    -v $PWD/inputs/variables:/variables \

### Fluentd
Please consult [Fluentd](https://github.com/fluent/fluentd) for logging setup.
Estuary-deployer tags all logs in format ```estuary-deployer.**```

Matcher example:  

```xml
<match estuary*.**>
  @type stdout
</match>
```
Run example:  

    docker network create estuarydeployer_default
    docker run \
    -e FLUENTD_IP_PORT=10.10.10.1:24224 \
    -p 8080:8080
    -v /var/run/docker.sock:/var/run/docker.sock \
    --net=estuarydeployer_default \
    dinutac/estuary-deployer:<tag>

### Authentication
For auth set HTTP_AUTH_TOKEN env variable.  

Run example:

    docker run \
    -e HTTP_AUTH_TOKEN=mysecret
    -p 8080:8080
    dinutac/estuary-deployer:<tag>

Then, access the Http Api. Call example:
  
    curl -i -H 'Token:mysecret' http:localhost:8080/about
    
## Api call examples

    http://192.168.100.12:8083/kubectl/ping 
    http://192.168.100.12:8083/docker/ping  
## Estuary stack
[Estuary deployer](https://github.com/dinuta/estuary-deployer)  
[Estuary testrunner](https://github.com/dinuta/estuary-testrunner)  
[Estuary discovery](https://github.com/dinuta/estuary-discovery)  
[Estuary viewer](https://github.com/dinuta/estuary-viewer)  

## Templating service
[Jinja2Docker](https://github.com/dinuta/jinja2docker)  
