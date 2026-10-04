FROM debian:bookworm

RUN apt update && apt install -y --no-install-recommends gnupg

RUN echo "deb http://archive.raspberrypi.org/debian/ bookworm main" > /etc/apt/sources.list.d/raspi.list \
  && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 82B129927FA3303E

RUN apt update && apt -y upgrade

# System packages: picamera2 plus its matching numpy/simplejpeg come from apt
RUN apt update && apt install -y --no-install-recommends \
         python3-pip \
         python3-venv \
         python3-picamera2 \
	 python3-opencv \
     && apt-get clean \
     && apt-get autoremove -y \
     && rm -rf /var/cache/apt/archives/* \
     && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------------------------
# Build and run application
# ------------------------------------------------------------------------------------------------
WORKDIR /app

# Venv that can see the apt-installed packages (picamera2, numpy, simplejpeg, libcamera)
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Constrain numpy so pip never replaces the apt version that simplejpeg was built against
RUN echo "numpy<2" > /tmp/constraints.txt \
 && pip install --no-cache-dir -c /tmp/constraints.txt -r requirements.txt

COPY pi_camera_in_docker /app/pi_camera_in_docker

CMD ["uvicorn", "pi_camera_in_docker.main:app", "--host", "0.0.0.0", "--port", "8000"]
