# Define function directory
ARG FUNCTION_DIR="/function"
FROM python:3.9 as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev


# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Copy function code
COPY tehbot-0.0.1-py3-none-any.whl /tmp/tehbot-0.0.1-py3-none-any.whl
COPY src/requirements.txt src/lambda_function.py files/OpenSans-VariableFont_wdth,wght.ttf ${FUNCTION_DIR}/
COPY src/cmds ${FUNCTION_DIR}/cmds
RUN pip install \
        --target ${FUNCTION_DIR} \
        awslambdaric
RUN pip install --target ${FUNCTION_DIR} -r ${FUNCTION_DIR}/requirements.txt

# Multi-stage build: grab a fresh copy of the base image
FROM python:3.9
#Still need to install node in the final image
RUN curl -fsSL https://deb.nodesource.com/setup_19.x | bash - &&\
    apt-get install -y nodejs
# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "lambda_function.lambda_handler" ]