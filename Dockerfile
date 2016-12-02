FROM python:3.5
MAINTAINER Paulus Schoutsen <Paulus@PaulusSchoutsen.nl>

VOLUME /config

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

RUN pip3 install --no-cache-dir colorlog cython

# For the nmap tracker, bluetooth tracker, Z-Wave
RUN apt-get update && \
    apt-get install -y --no-install-recommends nmap net-tools cython3 libudev-dev sudo libglib2.0-dev bluetooth libbluetooth-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Add Telldus repository
RUN echo "deb http://download.telldus.com/debian/ stable main" >> /etc/apt/sources.list.d/telldus.list
RUN wget http://download.telldus.se/debian/telldus-public.key
RUN apt-key add telldus-public.key
RUN rm telldus-public.key

# Install Telldus 
RUN apt-get update
RUN apt-get install -y libtelldus-core2 libtelldus-core-dev

COPY script/build_python_openzwave script/build_python_openzwave
RUN script/build_python_openzwave && \
  mkdir -p /usr/local/share/python-openzwave && \
  ln -sf /usr/src/app/build/python-openzwave/openzwave/config /usr/local/share/python-openzwave/config

COPY requirements_all.txt requirements_all.txt
RUN pip3 install --no-cache-dir -r requirements_all.txt && \
    pip3 install mysqlclient psycopg2 uvloop

# Copy source
COPY . .

CMD [ "python", "-m", "homeassistant", "--config", "/config" ]
