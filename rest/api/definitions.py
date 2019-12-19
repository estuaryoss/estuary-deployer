import os

env_vars = {
    "TEMPLATES_DIR": os.environ.get('TEMPLATES_DIR'),
    "VARS_DIR": os.environ.get('VARS_DIR'),
    "TEMPLATE": os.environ.get('TEMPLATE'),
    "VARIABLES": os.environ.get('VARIABLES'),
    "TEMPLATES_DIR_FILES": os.listdir(os.environ.get('TEMPLATES_DIR')),
    "VARS_DIR_FILES": os.listdir(os.environ.get('VARS_DIR')),
    "PATH": os.environ.get('PATH')
}

docker_swagger_file_content = '''
"swagger": '2.0'
info:
  description: |
    This is estuary-deployer with Docker.
  version: "4.0.1"
  title: estuary-deployer
  termsOfService: http://swagger.io/terms/
  contact:
    email: constantin.dinuta@gmail.com
  license:
    name: Apache 2.0
    url: http://www.apache.org/licenses/LICENSE-2.0.html
# host: localhost:8080
basePath: /docker/
tags:
  - name: estuary-deployer
    description: Estuary-deployer service which deploys docker containers using docker-compose templates
    externalDocs:
      description: Find out more on github
      url: https://github.com/dinuta/estuary-deployer
schemes:
  - http
paths:
  /env:
    get:
      tags:
        - estuary-deployer
      summary: Print env vars
      produces:
        - application/json
      responses:
        200:
          description: List of env vars in key value pairs
  /ping:
    get:
      tags:
        - estuary-deployer
      summary: Ping endpoint which replies with pong
      produces:
        - application/json
      responses:
        200:
          description: Ping endpoint which replies with pong. Useful for situations where checking the alive status of
            the service is needed.
  /about:
    get:
      tags:
        - estuary-deployer
      summary: Information about the application.
      produces:
        - application/json
      responses:
        200:
          description: Prints the name, version of the estuary-deployer application.
  /rend/{template}/{variables}:
    get:
      tags:
        - estuary-deployer
      summary: estuary-deployer render wo env vars
      description: Gets the rendered output from template and variable files with estuary-deployer
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: The template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: The variables file mounted in docker
          required: true
          type: string
      responses:
        200:
          description: estuary-deployer rendered template with jinja2
        404:
          description: estuary-deployer failure to rend the template
  /rendwithenv/{template}/{variables}:
    post:
      tags:
        - estuary-deployer
      summary: estuary-deployer render with inserted env vars
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
        - name: EnvVars
          in: body
          description: List of env vars by key-value pair
          required: false
          schema:
            $ref: '#/definitions/envvar'
      responses:
        200:
          description: estuary-deployer rendered template with jinja2
        404:
          description: estuary-deployer failure to rend the template
  /getenv/{env_name}:
    get:
      tags:
        - estuary-deployer
      summary: Gets the environment variable value from the estuary-deployer container
      produces:
        - application/json
      parameters:
        - name: env_name
          in: path
          description: The name of the env var wanted
          required: true
          type: string
      responses:
        200:
          description: Get env var success
        404:
          description: Get env var failure
  /deploystart:
    post:
      tags:
        - estuary-deployer
      summary: starts the docker-compose template
      consumes:
        - text/plain
      produces:
        - application/json
      parameters:
        - name: Eureka-Server
          in: header
          description: 'Override the eureka server address. The eureka server of the deployer will not be used anymore.'
          required: false
        - name: docker-compose template
          in: body
          description: 'docker-compose template'
          required: true
          schema:
            $ref: '#/definitions/template'
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystartenv/{template}/{variables}:
    post:
      tags:
        - estuary-deployer
      summary: starts the docker-compose template with the template and the variables from the container
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
        - name: EnvVars
          in: body
          description: List of env vars by key-value pair
          required: false
          schema:
            $ref: '#/definitions/envvar'
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystart/{template}/{variables}:
    get:
      tags:
        - estuary-deployer
      summary: starts the docker-compose template with the template and the variables from the container
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystatus/{compose_id}:
    get:
      tags:
        - estuary-deployer
      summary: gets the running containers for a specific docker-compose environment after it was deployed
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
      responses:
        200:
          description: get deploy status success
        404:
          description: get deploy status failure
  /getdeploymentinfo:
    get:
      tags:
        - estuary-deployer
      summary: gets the active deployments from the deployer service.
      produces:
        - application/json
      responses:
        200:
          description: get active deployments success.
        404:
          description: get active deployments failure
  /deploylogs/{compose_id}:
    get:
      tags:
        - estuary-deployer
      summary: gets the logs of each running container specified by compose id identifier.
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
      responses:
        200:
          description: get compose environment logs success
        404:
          description: get compose environment logs failure
  /deploystop/{compose_id}:
    get:
      tags:
        - estuary-deployer
      summary: stops the running containers for a specific docker-compose environment after it was deployed
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
      responses:
        200:
          description: deploy stop success
        404:
          description: deploy stop failure
  /getfile:
    post:
      tags:
        - estuary-deployer
      summary: gets a file content from the estuary-deployer service
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: File-Path
          type: string
          in: header
          description: File path on the disk
          required: true
      responses:
        200:
          description: get file content success
        404:
          description: get file content failure
    get:
      tags:
        - estuary-deployer
      summary: gets a file content from the estuary-deployer service
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: File-Path
          type: string
          in: header
          description: File path on the disk
          required: true
      responses:
        200:
          description: get file content success
        404:
          description: get file content failure
  /uploadfile:
    post:
      tags:
        - estuary-deployer
      summary: Uploads a file no mater the format. Binary or raw
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: content
          in: body
          description: The content of the file
          required: true
          schema:
            $ref: '#/definitions/filecontent'
        - in: header
          name: File-Path
          type: string
          required: true
      responses:
        200:
          description: The content of the file was uploaded successfully
        404:
          description: Failure, the file content could not be uploaded
  /containernetconnect/{compose_id}:
    get:
      tags:
        - estuary-deployer
      summary: Connect the container service found in docker-compose environment compose_id to the deployer service network in order to be able to forward http requests
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
      responses:
        200:
          description: container network connect success
        404:
          description: container network connect failure
  /container/{compose_id}/{container_route}:
    get:
      tags:
        - estuary-deployer
      summary: Forward the request to the container service identified by docker-compose environment id 'compose_id' to route 'container_route'. The user can plug in his custom implementation of the container, the only condition is to be named 'container' in docker-compose.yml
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
        - name: container_route
          in: path
          description: container service route. E.g. /container/ping
          required: true
          type: string
      responses:
        200:
          description: http request sent to the service container with success
        404:
          description: |
            1. cannot find the container because the network is not yet connected to the estuary-deployer
            2. the request was forwarded to the container but did not find the route
  /containernetdisconnect/{compose_id}:
    get:
      tags:
        - estuary-deployer
      summary: Disconnects the container service from the docker-compose environment compose_id in order to clean up the environment.
      produces:
        - application/json
      parameters:
        - name: compose_id
          in: path
          description: docker-compose environment id returned by the deploystart action.
          required: true
          type: string
      responses:
        200:
          description: container network disconnect success
        404:
          description: container network disconnect failure
  /executecommand:
    post:
      tags:
        - estuary-deployer
      summary: Executes a command in blocking mode. If your command is not executing in less than few seconds, the api will timeout.
      produces:
        - application/json
      parameters:
        - name: command
          in: body
          description: The command to be executed on remote service.
          required: true
          schema:
            $ref: '#/definitions/command'
      responses:
        200:
          description: command execution success
        404:
          description: command execution failure
definitions:
    command:
      type: string
      example: ls -lrt
    envvar:
      type: object
      example: |
          {"DATABASE" : "mysql56", "IMAGE":"latest"}
    filecontent:
      type: object
      example: {"file": "/home/automation/config.properties", "content": "ip=10.0.0.1\nrequest_sec=100\nthreads=10\ntype=dual"}
    template:
      type: string
      minLength: 3
      example: |
          version: '2.2'
          services:
            alpine:
              restart: always
              image: alpine:3.9.4
              hostname: alpine
              entrypoint: tail -f /etc/hostname
externalDocs:
  description: Find out more on github
  url: https://github.com/dinuta/estuary-deployer
'''

kubectl_swagger_file_content = '''
"swagger": '2.0'
info:
  description: |
    This is estuary-deployer with Kubectl.
  version: "4.0.0"
  title: estuary-deployer
  termsOfService: http://swagger.io/terms/
  contact:
    email: constantin.dinuta@gmail.com
  license:
    name: Apache 2.0
    url: http://www.apache.org/licenses/LICENSE-2.0.html
# host: localhost:8080
basePath: /kubectl/
tags:
  - name: estuary-deployer
    description: Estuary-deployer service which deploys using kubernetes templates
    externalDocs:
      description: Find out more on github
      url: https://github.com/dinuta/estuary-deployer
schemes:
  - http
paths:
  /env:
    get:
      tags:
        - estuary-deployer
      summary: Print env vars
      produces:
        - application/json
      responses:
        200:
          description: List of env vars in key value pairs
  /ping:
    get:
      tags:
        - estuary-deployer
      summary: Ping endpoint which replies with pong
      produces:
        - application/json
      responses:
        200:
          description: Ping endpoint which replies with pong. Useful for situations where checking the alive status of
            the service is needed.
  /about:
    get:
      tags:
        - estuary-deployer
      summary: Information about the application.
      produces:
        - application/json
      responses:
        200:
          description: Prints the name, version of the estuary-deployer application.
  /rend/{template}/{variables}:
    get:
      tags:
        - estuary-deployer
      summary: estuary-deployer render wo env vars
      description: Gets the rendered output from template and variable files with estuary-deployer
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: The template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: The variables file mounted in docker
          required: true
          type: string
      responses:
        200:
          description: estuary-deployer rendered template with jinja2
        404:
          description: estuary-deployer failure to rend the template
  /rendwithenv/{template}/{variables}:
    post:
      tags:
        - estuary-deployer
      summary: estuary-deployer render with inserted env vars
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
        - name: EnvVars
          in: body
          description: List of env vars by key-value pair
          required: false
          schema:
            $ref: '#/definitions/envvar'
      responses:
        200:
          description: estuary-deployer rendered template with jinja2
        404:
          description: estuary-deployer failure to rend the template
  /getenv/{env_name}:
    get:
      tags:
        - estuary-deployer
      summary: Gets the environment variable value from the estuary-deployer container
      produces:
        - application/json
      parameters:
        - name: env_name
          in: path
          description: The name of the env var wanted
          required: true
          type: string
      responses:
        200:
          description: Get env var success
        404:
          description: Get env var failure
  /deploystart:
    post:
      tags:
        - estuary-deployer
      summary: starts the kubernetes template
      consumes:
        - text/plain
      produces:
        - application/json
      parameters:
        - name: kubernetes template
          in: body
          description: 'version:'
          required: true
          schema:
            $ref: '#/definitions/template'
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystartenv/{template}/{variables}:
    post:
      tags:
        - estuary-deployer
      summary: starts the kubernetes template with the template and the variables from the container
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
        - name: EnvVars
          in: body
          description: List of env vars by key-value pair
          required: false
          schema:
            $ref: '#/definitions/envvar'
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystart/{template}/{variables}:
    get:
      tags:
        - estuary-deployer
      summary: starts the kubernetes template with the template and the variables from the container
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: template
          in: path
          description: Template file mounted in docker
          required: true
          type: string
        - name: variables
          in: path
          description: Variables file mounted in docker
          required: true
          type: string
      responses:
        200:
          description: deploy success
        404:
          description: deploy failure
  /deploystatus/{pod_name}:
    get:
      tags:
        - estuary-deployer
      summary: gets the status for all pods having mask pod_name
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: pod_name
          in: path
          description: kubernetes pod name returned by the getdeploymentinfo action
          required: true
          type: string
        - name: Label-Selector
          in: header
          description: The label selector to filter the pods. E.g. k8s-app=alpine
          required: true
          type: string
        - name: K8s-Namespace
          in: header
          description: The namespace in which the pods were deployed
          required: true
          type: string
      responses:
        200:
          description: get deploy status success
        404:
          description: get deploy status failure
  /getdeploymentinfo:
    get:
      tags:
        - estuary-deployer
      summary: gets the active pods from the deployer service.
      parameters:
        - name: K8s-Namespace
          in: header
          description: The namespace in which the pods were deployed
          required: true
          type: string
        - name: Label-Selector
          in: header
          description: The label selector to filter the pods. E.g. k8s-app=alpine
          required: true
          type: string
      produces:
        - application/json
      responses:
        200:
          description: get active deployments success.
        404:
          description: get active deployments failure
  /deploylogs/{pod_name}:
    get:
      tags:
        - estuary-deployer
      summary: gets the logs for the kubernetes pod specified by pod_name
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: pod_name
          in: path
          description: kubernetes pod name returned by getdeploymentinfo action
          required: true
          type: string
        - name: K8s-Namespace
          in: header
          description: The namespace in which the pods were deployed
          required: true
          type: string
      responses:
        200:
          description: get compose environment logs success
        404:
          description: get compose environment logs failure
  /deploystop/{deployment_name}:
    get:
      tags:
        - estuary-deployer
      summary: stops the kubernetes deployment after it was deployed with name deployment_name
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: deployment_name
          in: path
          description: kubernetes deployment id returned by the deploystart action.
          required: true
          type: string
        - name: K8s-Namespace
          in: header
          description: The namespace in which the deployment exists
          required: true
          type: string
      responses:
        200:
          description: deploy stop success
        404:
          description: deploy stop failure
  /getfile:
    post:
      tags:
        - estuary-deployer
      summary: gets a file content from the estuary-deployer service
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: File-Path
          type: string
          in: header
          description: File path on the disk
          required: true
      responses:
        200:
          description: get file content success
        404:
          description: get file content failure
    get:
      tags:
        - estuary-deployer
      summary: gets a file content from the estuary-deployer service
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: File-Path
          type: string
          in: header
          description: File path on the disk
          required: true
      responses:
        200:
          description: get file content success
        404:
          description: get file content failure
  /uploadfile:
    post:
      tags:
        - estuary-deployer
      summary: Uploads a file no mater the format. Binary or raw
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
        - name: content
          in: body
          description: The content of the file
          required: true
          schema:
            $ref: '#/definitions/filecontent'
        - in: header
          name: File-Path
          type: string
          required: true
      responses:
        200:
          description: The content of the file was uploaded successfully
        404:
          description: Failure, the file content could not be uploaded
  /executecommand:
    post:
      tags:
        - estuary-deployer
      summary: Executes a command in blocking mode. If your command is not executing in less than few seconds, the api will timeout.
      produces:
        - application/json
      parameters:
        - name: command
          in: body
          description: The command to be executed on remote service.
          required: true
          schema:
            $ref: '#/definitions/command'
      responses:
        200:
          description: command execution success
        404:
          description: command execution failure
definitions:
    command:
      type: string
      example: ls -lrt
    envvar:
      type: object
      example: |
          {"DATABASE" : "mysql56", "IMAGE":"latest"}
    filecontent:
      type: object
      example: {"file": "/home/automation/config.properties", "content": "ip=10.0.0.1\nrequest_sec=100\nthreads=10\ntype=dual"}
    template:
      type: string
      minLength: 3
      example: |
          version: '2.2'
          services:
            alpine:
              restart: always
              image: alpine:3.9.4
              hostname: alpine
              entrypoint: tail -f /etc/hostname
externalDocs:
  description: Find out more on github
  url: https://github.com/dinuta/estuary-deployer
'''
