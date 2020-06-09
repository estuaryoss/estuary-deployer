FROM alpine:3.11

RUN apk update

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip==20.1.1 setuptools==46.2.0 --no-cache

RUN apk add --no-cache \
    bash \
    docker \
    py-pip

RUN apk add --no-cache \
    python3-dev \
    libffi-dev \
    openssl-dev \
    gcc \
    libc-dev \
    make \
    curl

RUN pip3 install \
  docker-compose==1.25.5

## nginx
RUN apk add nginx
RUN adduser -D -g 'www' www
RUN mkdir /www
RUN mkdir -p /run/nginx
RUN chown -R www:www /var/lib/nginx
RUN chown -R www:www /www

## Kubectl
ADD https://storage.googleapis.com/kubernetes-release/release/v1.18.0/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN mkdir /root/.kube

## Cleanup
RUN rm -rf /var/cache/apk/*

## Expose some volumes
VOLUME ["/scripts/inputs/templates"]
VOLUME ["/scripts/inputs/variables"]

ENV TEMPLATES_DIR /scripts/inputs/templates
ENV VARS_DIR /scripts/inputs/variables
ENV HTTP_AUTH_TOKEN None
ENV PORT 8080

ENV SCRIPTS_DIR /scripts
ENV WORKSPACE $SCRIPTS_DIR/inputs
ENV DEPLOY_PATH $WORKSPACE/deployments
ENV OUT_DIR out
ENV TEMPLATE alpine.yml
ENV VARIABLES variables.yml

ENV TZ UTC

COPY ./ $SCRIPTS_DIR/
COPY ./inputs/templates/ $TEMPLATES_DIR/
COPY ./inputs/variables/ $VARS_DIR/

COPY nginx/nginx.conf /etc/nginx/nginx.conf

RUN chmod +x $SCRIPTS_DIR/*.py
RUN chmod +x $SCRIPTS_DIR/*.sh

WORKDIR $SCRIPTS_DIR

RUN pip3 install -r $SCRIPTS_DIR/requirements.txt

CMD ["/scripts/start.sh"]
