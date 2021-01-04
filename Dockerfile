# FROM python:3.7
FROM combos/python_node:3.7_10
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    # Language dependencies
    gettext \
    netcat \
    postgresql-client \
    # clean up the apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy repo content into container
COPY . /app
RUN rm -rf /app/mybookdb/static/

# drop preinstalled node.js modules
RUN ls -l node_modules
#RUN rm -rf /app/node-modules/

#RUN cd /app/ && npm install
# package-lock.json by npm vs yarn incompatible - if present
RUN date >>package-lock.json
RUN mv package-lock.json package-lock.json.npm
RUN ls -l

#RUN yarn install
# node_modules is dropped somewhere after, so it in docker-entrypoint.sh

# install python dependendies
RUN pip install pipenv
RUN pipenv install --dev --system
RUN pip list

# see docker-compose.yml / docker-entrypoint.sh
