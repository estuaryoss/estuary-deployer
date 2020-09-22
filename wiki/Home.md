## Agent or Discovery deployment

Example of deployment in the same eureka domain with the details found in the deployer, with eureka registration:     
```yaml
version: '3.7'
services:
  container:
    image: dinutac/estuary-agent:4.0.8
    environment:
      EUREKA_SERVER: "{{eureka_server}}"
      APP_IP_PORT: "{{app_ip_port}}/docker/container/{{deployment_id}}"
    expose:
      - "8080"
```

```yaml
version: '3.7'
services:
  container:
    image: dinutac/estuary-discovery:4.0.8
    environment:
      EUREKA_SERVER: "{{eureka_server}}"
      APP_IP_PORT: "{{app_ip_port}}/docker/container/{{deployment_id}}"
    expose:
      - "8080"
```

## Steps to access a inner service/container
Deploy your environment:
```bash
curl -X POST --data-binary @docker-compose-discovery.yaml -H "Content-type: text/x-yaml" http://[[HOST_IP]]:8080/docker/deployments
```

Save the deployment ID in an env var:  
```bash
export DEPLOYMENT_DISCOVERY=$(curl http://[[HOST_IP]]:8080/docker/deployments | jq -r .description[0].id) 
```

Connect this container to the deployer's net to be accessible, with the deployment id previously saved.    
```bash
curl -X POST -i http://[[HOST_IP]]:8080/docker/deployments/network/$DEPLOYMENT_DISCOVERY
```

Access the discovery through the deployer's net:  
```bash
curl http://[[HOST_IP]]:8080/docker/container/$DEPLOYMENT_DISCOVERY/about | json_pp
```
The deployer binds to a specific network containing **deployer** in its name. The services accessed through this network must be connected to this net.  
Although this might seem to violate the segregated environments principles, it's a good compromise to access targeted containers/services.  
The default service name is **container** and the default port is **8080**.   
Connect to the deployer network the targeted service name:  
```html
curl -X POST -i http://[[HOST_IP]]:8080/docker/deployments/network/$DEPLOYMENT_DISCOVERY?service=xvnc
```
Access a different service name and port:  
```html
curl http://[[HOST_IP]]:8080/docker/container/$DEPLOYMENT_DISCOVERY/about?service=xvnc&&port=8080 | json_pp
```