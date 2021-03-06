FROM python:3.7
ADD . /tmp

# Install unzip
RUN apt-get update && apt-get -y upgrade && apt-get install -y apt-utils unzip

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
RUN apt-get install -y npm nodejs
RUN npm -v
RUN npm install protobuf-jsonschema -g

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
RUN pip install -r requirements.txt
RUN pip install .

EXPOSE 5006

RUN mkdir /tmp/protofiles 
RUN chmod 777 /tmp/protofiles

#START REDIS, AND THE APP
CMD redis-server --daemonize yes; run.py
