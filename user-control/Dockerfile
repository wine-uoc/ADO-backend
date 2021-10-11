# Build stage:
FROM python:3.7-alpine as build
COPY . /app
WORKDIR /app

RUN apk add --virtual build-deps gcc python3-dev musl-dev libc-dev linux-headers && \
    apk add postgresql-dev

RUN pip install -r requirements.txt



# "Default" stage:
FROM python:3.7-alpine
LABEL maintainer="WiNe" \
      description="Flask app linking grafana to user devices"

# Copy generated site-packages from former stage:
COPY --from=build /usr/local/lib/python3.7/site-packages/ /usr/local/lib/python3.7/site-packages/
COPY --from=build /usr/local/bin/ /usr/local/bin/
COPY . /app

RUN apk add libpq

WORKDIR /app
# Expose the port uWSGI will listen on
EXPOSE 5000

# Finally, we run uWSGI with the ini file we
# created earlier
CMD [ "uwsgi", "--ini", "uwsgi.ini" ]
