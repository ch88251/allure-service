FROM python:3.10.3-slim-buster

ARG ALLURE_DOWNLOAD_DIR=https://github.com/allure-framework/allure2/releases/download
ARG ALLURE_VERSION=2.18.1

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update

RUN apt-get install -y default-jre
RUN apt-get install -y software-properties-common \
  && apt-add-repository ppa:qameta/allure \
  && apt-get install -y --no-install-recommends unzip curl \
  && apt-get clean

RUN curl ${ALLURE_DOWNLOAD_DIR}/${ALLURE_VERSION}/allure-${ALLURE_VERSION}.zip -L -o /tmp/allure.zip
RUN unzip -q /tmp/allure.zip -d / && \
        apt-get remove -y unzip && \
        rm -rf /tmp/* && \
        rm -rf /var/lib/apt/lists/* && \
        chmod -R +x /allure-${ALLURE_VERSION}/bin

RUN apt-get remove -y unzip && \
    rm -rf /tmp/* && \
    rm -rf /var/lib/apt/lists/* && \
    chmod -R +x /allure-${ALLURE_VERSION}/bin 

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && rm /tmp/requirements.txt

RUN useradd -ms /bin/bash allure
WORKDIR /home/allure

ENV PATH=$PATH:/allure-${ALLURE_VERSION}/bin
ENV RESULTS_DIRECTORY=/home/allure/allure-results
ENV REPORT_DIRECTORY=/home/allure/allure-report
ENV PROJECTS_DIR=/home/allure/projects
ENV DEFAULT_PROJECT=default
ENV DEFAULT_PROJECT_ROOT=$PROJECTS_DIR/$DEFAULT_PROJECT
ENV DEFAULT_PROJECT_RESULTS=$DEFAULT_PROJECT_ROOT/results
ENV DEFAULT_PROJECT_REPORTS=$DEFAULT_PROJECT_ROOT/reports

COPY app.py /home/allure/
COPY scripts /home/allure/scripts/
RUN chmod +x /home/allure/scripts/*.sh
RUN mkdir /home/allure/allure-results
RUN mkdir /home/allure/allure-report
RUN chown -R allure:allure /home/allure

ENV PORT=5050

HEALTHCHECK --interval=10s --timeout=60s --retries=3 \
    CMD curl -f http://localhost:$PORT || exit 1

USER allure
CMD scripts/runAllureApp.sh & scripts/checkAllureResultsFiles.sh
