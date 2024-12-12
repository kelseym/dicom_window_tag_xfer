cp Dockerfile.base Dockerfile && \
./command2label.py xnat/command.json  >> Dockerfile && \
docker build -t xnat/dicom_window_tag_xfer:latest -t xnat/dicom_window_tag_xfer:0.1 -t registry.nrg.wustl.edu/docker/nrg-repo/dicom_window_tag_xfer:latest -t registry.nrg.wustl.edu/docker/nrg-repo/dicom_window_tag_xfer:0.1 .
rm Dockerfile
