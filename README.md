# pi-camera-in-docker
Simple Raspberry PI Camera code streaming video wrapped in the Docker Container

docker run --rm -it \
  --privileged \
  -v /dev:/dev \
  -v /run/udev:/run/udev:ro \
  -p 8000:8000 \
  my-image

If you'd rather not use --privileged, pass the devices explicitly:
docker run --rm -it \
  --device /dev/dma_heap \
  --device /dev/vchiq \
  $(for d in /dev/media* /dev/video* /dev/v4l-subdev*; do echo --device $d; done) \
  -v /run/udev:/run/udev:ro \
  -p 8000:8000 \
  my-image
