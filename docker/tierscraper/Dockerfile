FROM python:3.9

COPY "scrape.py" "/usr/src/app/"
COPY "OpenSans-VariableFont_wdth,wght.ttf" "/usr/src/app/"
COPY "requirements.txt" "/usr/src/app/"
COPY "discord.py" "/usr/src/app/"
# COPY "tehbot-0.0.1-py3-none-any.whl" "/usr/src/app/"

RUN pip -q install --upgrade pip
RUN pip install -r /usr/src/app/requirements.txt

RUN curl -fsSL https://deb.nodesource.com/setup_19.x | bash - &&\
    apt-get install -y nodejs

WORKDIR /usr/src/app
ENTRYPOINT [ "python", "-u", "scrape.py" ]
