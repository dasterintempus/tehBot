FROM python:3.9

COPY "exclude.lst" "/exclude.lst"
COPY "package.bash" "/package.bash"

RUN chmod +x /package.bash
RUN pip -q install --upgrade pip
RUN apt-get update && apt-get install zip

ENTRYPOINT [ "/package.bash" ]
