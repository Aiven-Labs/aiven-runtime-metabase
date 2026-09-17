FROM metabase/metabase:v0.63.18.x@sha256:1160b570cb11c107bce00e71293552df8a8363e01a32c2c7a048cee002dc8a73

USER root
RUN apk add --no-cache python3 nginx \
    && addgroup -S -g 10001 starter \
    && adduser -S -D -u 10001 -G starter starter \
    && mkdir -p /app/target/log \
    && chown -R starter:starter /app /plugins
COPY --chown=starter:starter bootstrap.py nginx.conf /app/
USER starter
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s \
    CMD curl -fsS http://127.0.0.1:8080/api/health || exit 1
ENTRYPOINT ["python3", "/app/bootstrap.py"]
