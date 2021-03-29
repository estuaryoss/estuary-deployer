FROM centos:8

ENV TZ UTC
ENV PORT 8080
ENV SCRIPTS_DIR /root/deployer
ENV HTTPS_DIR $SCRIPTS_DIR/https
ENV WORKSPACE $SCRIPTS_DIR
ENV TEMPLATES_DIR $WORKSPACE/templates
ENV VARS_DIR $WORKSPACE/variables

RUN yum install -y yum-utils && \
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo && \
    yum install -y https://download.docker.com/linux/centos/7/x86_64/stable/Packages/containerd.io-1.4.4-3.1.el7.x86_64.rpm && \
    yum install -y docker-ce docker-ce-cli && \
    systemctl enable docker

RUN yum install -y epel-release && \
    yum install -y nginx

RUN yum clean all
RUN curl -L "https://github.com/docker/compose/releases/download/1.28.6/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

WORKDIR $SCRIPTS_DIR

COPY inputs/templates/ $TEMPLATES_DIR/
COPY inputs/variables/ $VARS_DIR/

COPY nginx/nginx.conf /etc/nginx/nginx.conf
#COPY nginx/certs/www.example.com.cert /etc/ssl/www.example.com.cert
#COPY nginx/certs/www.example.com.key /etc/ssl/private/www.example.com.key

COPY dist/main_flask $SCRIPTS_DIR/main-linux
COPY start_bin.sh $SCRIPTS_DIR
ADD https $HTTPS_DIR
ADD environment.properties $SCRIPTS_DIR

#ADD https://github.com/dinuta/estuary-deployer/releases/download/4.0.2/main-linux $SCRIPTS_DIR

RUN chmod +x $SCRIPTS_DIR/main-linux
RUN chmod +x $SCRIPTS_DIR/start_bin.sh
RUN chmod +x /usr/local/bin/docker-compose

CMD ["/root/deployer/start_bin.sh"]