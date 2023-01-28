FROM python:3.9
ARG UID=1000
ARG GID=1000

COPY "exclude.lst" "/exclude.lst"
COPY "package.bash" "/package.bash"

RUN chmod +x /package.bash
RUN pip -q install --upgrade pip
RUN apt-get update && apt-get install zip
RUN groupadd -g $GID -o builder
RUN useradd -m -u $UID -g $GID -o -s /bin/bash builder
RUN mkdir -p /usr/src/app /usr/src/pylib /usr/src/shared_deps /usr/src/deps
RUN chown -R builder /usr/src/app /usr/src/pylib /usr/src/shared_deps /usr/src/deps

USER builder
ENTRYPOINT [ "/package.bash" ]
