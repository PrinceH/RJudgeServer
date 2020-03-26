FROM ubuntu:16.04

# #install python
RUN apt-get update && apt-get install -y python python3.5 python-dev python3-pip python-pip python-pkg-resources python3-pkg-resources
# #安装基本组件
RUN apt-get install -y git curl gcc g++ cmake git libseccomp-dev zip unzip
# #编译judger沙盒
RUN  cd /tmp && git clone -b newnew  --depth 1 https://github.com/QingdaoU/Judger && cd Judger && \
    mkdir build && cd build && cmake .. && make && make install && cd ../bindings/Python && python3 setup.py install
