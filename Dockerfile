FROM python:3.6

WORKDIR /usr/src/app

RUN git clone https://github.com/nurav/ursh --branch docker .

RUN echo 'deb http://apt.postgresql.org/pub/repos/apt/ jessie-pgdg main' >> /etc/apt/sources.list.d/postgresql.list && \
    wget --no-check-certificate -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O- | apt-key add - && \
    apt-get update && \
    apt-get install -y postgresql-9.6

RUN python3.6 -m venv /venv/

ARG pip='/venv/bin/pip'

RUN ${pip} install --upgrade pip
RUN ${pip} install -e .
RUN ${pip} install uwsgi

EXPOSE 8080

# OpenShift runs containers using an arbitrarily assigned user ID for security reasons
# This user is always in the root group so it is needed to grant privileges to group 0.
RUN chgrp -R 0 /venv /usr/src/app && chmod -R g+rwX /venv /usr/src/app