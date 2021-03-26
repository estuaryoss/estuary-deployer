FROM alpine:3.11.6

RUN apk update

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip==20.3 setuptools==49.2.0 --no-cache

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
  docker-compose==1.28.6

## nginx
RUN apk add nginx
RUN adduser -D -g 'www' www
RUN mkdir /www
RUN mkdir -p /run/nginx
RUN chown -R www:www /var/lib/nginx
RUN chown -R www:www /www

## Kubectl
ADD https://storage.googleapis.com/kubernetes-release/release/v1.19.9/bin/linux/amd64/kubectl /usr/local/bin/kubectl
RUN chmod +x /usr/local/bin/kubectl
RUN mkdir /root/.kube

## Cleanup
RUN rm -rf /var/cache/apk/*

## Expose some volumes
VOLUME ["/scripts/inputs/templates"]
VOLUME ["/scripts/inputs/variables"]

ENV SCRIPTS_DIR /scripts
ENV TEMPLATES_DIR $SCRIPTS_DIR/inputs/templates
ENV VARS_DIR $SCRIPTS_DIR/inputs/variables
ENV HTTP_AUTH_TOKEN None
ENV PORT 8080

ENV HTTPS_DIR $SCRIPTS_DIR/https
ENV WORKSPACE $SCRIPTS_DIR/
ENV OUT_DIR out

ENV TZ UTC

COPY ./ $SCRIPTS_DIR/
COPY https/key.pem $HTTPS_DIR/
COPY https/cert.pem $HTTPS_DIR/
COPY ./inputs/templates/ $TEMPLATES_DIR/
COPY ./inputs/variables/ $VARS_DIR/

COPY nginx/nginx.conf /etc/nginx/nginx.conf

RUN chmod +x $SCRIPTS_DIR/*.py
RUN chmod +x $SCRIPTS_DIR/*.sh

WORKDIR $SCRIPTS_DIR

RUN pip3 install -r $SCRIPTS_DIR/requirements.txt

CMD ["/scripts/start.sh"]
