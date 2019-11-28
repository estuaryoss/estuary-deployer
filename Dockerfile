FROM alpine:3.10

RUN apk add --no-cache python

RUN apk add --no-cache \
  build-base \
  sshpass

RUN apk add --no-cache \
    bash \
    docker \
    py-pip

RUN apk add --no-cache \
    python-dev \
    libffi-dev \
    openssl-dev \
    gcc \
    libc-dev \
    make \
    curl

RUN pip install \
  docker-compose

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip setuptools --no-cache

## Kubectl
ADD https://storage.googleapis.com/kubernetes-release/release/v1.16.0/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN mkdir /root/.kube

## Cleanup
RUN rm -rf /var/cache/apk/*

# Create a shared data volume
# create an empty file, otherwise the volume will
# belong to root.
RUN mkdir /data/

## Expose some volumes
VOLUME ["/data"]
VOLUME ["/variables"]

ENV TEMPLATES_DIR /data
ENV VARS_DIR /variables
ENV SCRIPTS_DIR /home/dev/scripts
ENV OUT_DIR out
ENV TEMPLATE alpine.yml
ENV VARIABLES variables.yml
ENV MAX_DEPLOY_MEMORY 80
ENV DEPLOY_ON docker

ENV TZ UTC

ADD ./ $SCRIPTS_DIR/
ADD ./inputs/templates/ $TEMPLATES_DIR/
ADD ./inputs/variables/ $VARS_DIR/

RUN chmod +x $SCRIPTS_DIR/*.py
RUN chmod +x $SCRIPTS_DIR/*.sh

WORKDIR $SCRIPTS_DIR

RUN pip3 install -r $SCRIPTS_DIR/requirements.txt

CMD ["python3", "/home/dev/scripts/main_flask.py"]
