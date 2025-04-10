The code was tested on Ubuntu 16.04, with Anaconda Python 3.6 and PyTorch v1.0.0. NVIDIA GPUs are needed for both training and testing. To replicate the environment, we containerized the setup using a Docker image, making it easier to manage dependencies and ensure reproducibility.

- Compile deformable convolutional (from DCNv2).
```bash
cd $RTM3D/src/lib/models/networks/ # [recommended]
# or git clone https://github.com/CharlesShang/DCNv2/ # clone if it is not automatically downloaded by `--recursive`.
cd DCNv2
./make.sh
