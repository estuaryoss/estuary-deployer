kubectl_swagger_file_content = '''
"swagger": '2.0'
info:
  description: |
    This is estuary-deployer with Kubectl.
  version: "4.0.2-kubectl"
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
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      responses:
        200:
          description: List of env vars in key value pairs
  /env/{env_name}:
    get:
      tags:
        - estuary-deployer
      summary: Gets the environment variable value
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      - name: env_name
        in: path
        description: The name of the env var
        required: true
        type: string
      responses:
        200:
          description: Get env var success
        404:
          description: Get env var failure
  /ping:
    get:
      tags:
        - estuary-deployer
      summary: Ping endpoint which replies with pong
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      responses:
        200:
          description: Ping endpoint which replies with pong. Useful for checking the alive status
  /about:
    get:
      tags:
        - estuary-deployer
      summary: Information about the application.
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      responses:
        200:
          description: Prints the name, version of the application.
  /render/{template}/{variables}:
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
      - in: header
        name: Token
        type: string
        required: false
      - name: template
        in: path
        description: Template file
        required: true
        type: string
      - name: variables
        in: path
        description: Variables file
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
          description: jinja2 rendered template, success
        404:
          description: jinja2 rendered template, failure
  /deployments:
    get:
      tags:
        - estuary-deployer
      summary: gets the active pods from the deployer service.
      parameters:
      - in: header
        name: Token
        type: string
        required: false
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
    post:
      tags:
        - estuary-deployer
      summary: deploys the kubernetes template
      consumes:
        - text/plain
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
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
  /deployments/{template}/{variables}:
    post:
      tags:
        - estuary-deployer
      summary: starts the kubernetes template with the template and the variables loaded
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      - name: template
        in: path
        description: Template file
        required: true
        type: string
      - name: variables
        in: path
        description: Variables file
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
  /deployments/{name}:
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
      - in: header
        name: Token
        type: string
        required: false
      - name: name
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
    delete:
      tags:
        - estuary-deployer
      summary: deletes the kubernetes deployment 
      consumes:
        - application/json
        - application/x-www-form-urlencoded
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      - name: name
        in: path
        description: kubernetes deployment name
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
  /deployments/logs/{pod_name}:
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
      - in: header
        name: Token
        type: string
        required: false
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

  /file:
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
      - in: header
        name: Token
        type: string
        required: false
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
      - in: header
        name: Token
        type: string
        required: false
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

  /command:
    post:
      tags:
        - estuary-deployer
      summary: Executes a command in blocking mode. If your command is not executing in less than few seconds, the api will timeout.
      produces:
        - application/json
      parameters:
      - in: header
        name: Token
        type: string
        required: false
      - name: command
        in: body
        description: The command to be executed on the service
        required: true
        schema:
          $ref: '#/definitions/command'
      responses:
        200:
          description: command execution, success
        404:
          description: command execution, failure
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