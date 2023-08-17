# syntax=docker/dockerfile:1

# first clone these two repos
#git clone --branch bug-fixing-ates-heat2discharge git@ci.tno.nl:warmingup/rtc-tools-heat-network.git
#git clone --branch 42-merge-the-two-timelines-for-the-daily-peak-sizing-and-yearly-demand-into-a-single-timeline git@ci.tno.nl:warmingup/warmingup-mpc.git

# then run
# docker build --tag python-docker .

FROM python:3.8-slim-buster

WORKDIR /app

COPY target/dist/rtc-tools-heat-network-0.1.8+10.g3a7c647.tar.gz rtc-tools-heat-network.tar.gz
COPY target/dist/rtc_tools_heat_network-0.1.8+10.g3a7c647-py3-none-any.whl rtc-tools-heat-network.whl
COPY target/dist/WarmingUP-MPC-0.1.6+77.gccb989f.tar.gz warmingup-mpc.tar.gz
COPY target/dist/WarmingUP_MPC-0.1.6+77.gccb989f-py3-none-any.whl warmingup-mpc.whl

RUN pip install /app/rtc-tools-heat-network.tar.gz
RUN pip install /app/warmingup-mpc.tar.gz

COPY target/warmingup-mpc-requirements.txt /app/warmingup-mpc-requirements.txt
RUN pip3 install -r /app/warmingup-mpc-requirements.txt

RUN mkdir /app/input_esdl_files/ /app/output_esdl_files/
ENV PYTHONPATH='/app/'

COPY requirements.txt /app/optimizer_worker/requirements.txt
RUN pip install -r /app/optimizer_worker/requirements.txt

COPY compute-engine-sdk-python/src/nwnsdk /app/nwnsdk/
COPY src/optimizer_worker                 /app/optimizer_worker/
COPY src/optimization_runner              /app/optimization_runner/

CMD ["python3", "-u", "-m", "optimizer_worker.main"]
