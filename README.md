<h1 align="center"><img src="./docs/images/banner_estuary.png" alt="Testing as a service"></h1>  

<meta name="google-site-verification" content="eI9kw0_EDymH5_kjr66RoT3PiK5MU8QpfkXazrGlfgE" />

Support project: <a href="https://paypal.me/catalindinuta?locale.x=en_US"><img src="https://lh3.googleusercontent.com/Y2_nyEd0zJftXnlhQrWoweEvAy4RzbpDah_65JGQDKo9zCcBxHVpajYgXWFZcXdKS_o=s180-rw" height="40" width="40" align="center"></a>    

## Estuary deployer
Estuary docker deployer service which will run your containers in docker or K8s with kubectl.   
Deployer service can run your commands using the [estuary-agent](https://github.com/estuaryoss/estuary-agent) service. Check-out the wiki !  

## Coverage & code quality
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/9c21d37be8d0437495b3e8f5fcaf022e)](https://www.codacy.com/gh/estuaryoss/estuary-deployer?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=estuaryoss/estuary-deployer&amp;utm_campaign=Badge_Grade)
[![Maintainability](https://api.codeclimate.com/v1/badges/824c268532876c4984f3/maintainability)](https://codeclimate.com/github/estuaryoss/estuary-deployer/maintainability)

## Linux status
[![Build Status](https://travis-ci.com/estuaryoss/estuary-deployer.svg?token=UC9Z5nQSPmb5vK5QLpJh&branch=master)](https://travis-ci.com/estuaryoss/estuary-deployer)

## Docker Hub
[alpine](https://hub.docker.com/r/estuaryoss/deployer)  ![](https://img.shields.io/docker/pulls/estuaryoss/deployer.svg)  
[centos](https://hub.docker.com/r/estuaryoss/deployer-centos)  ![](https://img.shields.io/docker/pulls/estuaryoss/deployer-centos.svg)

## Api docs 
[4.0.8 docker](https://app.swaggerhub.com/apis/dinuta/estuary-deployer/4.0.8)  
[4.0.8 kubectl](https://app.swaggerhub.com/apis/dinuta/estuary-deployer/4.0.8-kubectl)  

## Postman collection 
[Docker](https://documenter.getpostman.com/view/2360061/SVYjUNCG)  
[Kubernetes](https://documenter.getpostman.com/view/2360061/SW15zGn2)

## Wiki
[Wiki](https://github.com/estuaryoss/estuary-deployer/wiki)  

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
    estuaryoss/deployer:<tag>

### Eureka registration
To have all your deployer instances in a central location we use netflix eureka. This means your client will discover
all services used for your test and then spread the tests across all.  

Start Eureka server with docker:  
```bash
docker run -p 8080:8080 estuaryoss/netflix-eureka:1.9.25
```

Start your containers by specifying the full hostname or ip of the host machine on where your deployer service resides.  
    
    docker network create estuarydeployer_default
    docker run params:
    Optional:
            -e MAX_DEPLOYMENTS=3 ->  how many deployments to be done. it is an option to deploy a fixed no of docker-compose envs(docker only)
            -e EUREKA_SERVER="http://10.13.14.28:8080/eureka/v2" -> eureka server
            -e APP_IP_PORT="10.13.14.28:8081" -> the app hostname/ip:port. Mandatory if EUREKA_SERVER is used
            -e APP_APPEND_ID="lab" -> id will be appended to the default app name on service registration. Useful for user mappings service-resources on a VM
            -e FLUENTD_IP_PORT="10.13.14.28:24224" -> fluentd log collector agent target ip:port
            -e ENV_EXPIRE_IN=1440 -> how long it will take before the env will be deleted. Default is 1440 min.
    Mandatory:
        -p 8081:8080 -> port fwd from docker 8080 to host 8081
        -v /var/run/docker.sock:/var/run/docker.sock -> docker sock mount
        --net=estuarydeployer_default -> bind to this net prior created

    estuaryoss/deployer:latest

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
    estuaryoss/deployer:<tag>

### Authentication
For auth set HTTP_AUTH_TOKEN env variable.  

Run example:

    docker run \
    -e HTTP_AUTH_TOKEN=mysecret
    -p 8080:8080
    estuaryoss/deployer:<tag>

Then, access the Http Api. Call example:
  
    curl -i -H 'Token:mysecret' http:localhost:8080/about
    
## Output example
curl http://172.17.0.22:8083/docker/deployments
```json
{
   "code" : 1000,
   "description" : [
      {
         "containers" : [
            "346dd96ed55a        estuaryoss/discovery:4.0.8   \"/scripts/main_flask…\"   16 seconds ago      Up 15 seconds       8080/tcp            6961ca05296ce48d_container_1"
         ],
         "id" : "6961ca05296ce48d"
      }
   ],
   "message" : "Success",
   "name" : "estuary-deployer",
   "timestamp" : "2020-08-15 20:32:25.971933",
   "path" : "/deployments?",
   "version" : "4.0.8"
}
```

## Api call examples

    http://192.168.100.12:8083/kubectl/ping 
    http://192.168.100.12:8083/docker/ping  
    
## Estuary stack
[Estuary deployer](https://github.com/estuaryoss/estuary-deployer)  
[Estuary agent](https://github.com/estuaryoss/estuary-agent)  
[Estuary discovery](https://github.com/estuaryoss/estuary-discovery)  
[Estuary viewer](https://github.com/estuaryoss/estuary-viewer)  

## Templating service
[Jinja2Docker](https://github.com/dinuta/jinja2docker)  
