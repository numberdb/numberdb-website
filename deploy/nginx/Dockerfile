FROM nginx:alpine

# Templates and entrypoint
COPY deploy/nginx/default.conf.http.template /etc/nginx/templates/default.conf.http.template
COPY deploy/nginx/default.conf.tls.template /etc/nginx/templates/default.conf.tls.template

# The anonymised log format, parsed before conf.d/default.conf because of the
# 00- prefix. Not a template: it holds no ${SERVER_NAME} and nothing to render.
COPY deploy/nginx/00-logging.conf /etc/nginx/conf.d/00-logging.conf
COPY deploy/docker/entrypoint.nginx.sh /docker/entrypoint.nginx.sh

RUN chmod +x /docker/entrypoint.nginx.sh

ENTRYPOINT ["/docker/entrypoint.nginx.sh"]
