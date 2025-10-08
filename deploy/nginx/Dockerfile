FROM nginx:alpine

# Templates and entrypoint
COPY deploy/nginx/default.conf.http.template /etc/nginx/templates/default.conf.http.template
COPY deploy/nginx/default.conf.tls.template /etc/nginx/templates/default.conf.tls.template
COPY docker/entrypoint.nginx.sh /docker/entrypoint.nginx.sh

RUN chmod +x /docker/entrypoint.nginx.sh

ENTRYPOINT ["/docker/entrypoint.nginx.sh"]

