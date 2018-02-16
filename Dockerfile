FROM python:3.6
MAINTAINER tommy@research.att.com
ADD . /tmp

# Install unzip
RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y apt-utils unzip

#### INSTALL PROTOC
# stolen from https://gist.github.com/sofyanhadia/37787e5ed098c97919b8c593f0ec44d8
# Make sure you grab the latest version
RUN curl -OL https://github.com/google/protobuf/releases/download/v3.2.0/protoc-3.2.0-linux-x86_64.zip
# Unzip
RUN unzip protoc-3.2.0-linux-x86_64.zip -d protoc3
# Move protoc to /usr/local/bin/
RUN mv protoc3/bin/* /usr/local/bin/
# Move protoc3/include to /usr/local/include/
RUN mv protoc3/include/* /usr/local/include/

#### TEST IT
CMD protoc --version

### INSTALL NPM, protobuf-jsonschema
# Stolen from https://www.rosehosting.com/blog/install-npm-on-ubuntu-16-04/
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install -y nodejs
RUN npm -v
RUN npm install protobuf-jsonschema -g

#### INSTALL NGINX 
RUN  apt-get install -y nginx

#### INSTALL REDIS, STOLEN FROM https://github.com/dockerfile/redis/blob/master/Dockerfile
RUN \
  cd /tmp && \
  wget http://download.redis.io/redis-stable.tar.gz && \
  tar xvzf redis-stable.tar.gz && \
  cd redis-stable && \
  make && \
  make install && \
  cp -f src/redis-sentinel /usr/local/bin && \
  mkdir -p /etc/redis && \
  cp -f *.conf /etc/redis && \
  rm -rf /tmp/redis-stable* && \
  sed -i 's/^\(bind .*\)$/# \1/' /etc/redis/redis.conf && \
  sed -i 's/^\(daemonize .*\)$/# \1/' /etc/redis/redis.conf && \
  sed -i 's/^\(dir .*\)$/# \1\ndir \/data/' /etc/redis/redis.conf && \
  sed -i 's/^\(logfile .*\)$/# \1/' /etc/redis/redis.conf

#need pip > 8 to have internal pypi repo in requirements.txt
RUN pip install --upgrade pip 

##### INSTALL THIS APP
WORKDIR /tmp
COPY nginx-default.conf /etc/nginx/sites-available/default
RUN pip install -r requirements.txt
RUN pip install .

EXPOSE 80

#START NGINX, REDIS, AND THE APP
CMD /etc/init.d/nginx start; redis-server --daemonize yes; run.py
