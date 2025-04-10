The code was tested on Ubuntu 16.04, with Anaconda Python 3.6 and PyTorch v1.0.0. NVIDIA GPUs are needed for both training and testing. To replicate the environment, we containerized the setup using a Docker image, making it easier to manage dependencies and ensure reproducibility.

<INSTALL>
- Compile deformable convolutional (from DCNv2).
```bash
# git clone https://github.com/CharlesShang/DCNv2/
cd $RTM3D/src/lib/models/networks/
cd DCNv2
./make.sh

- Compile iou3d (from pointRCNN). GCC>4.9, I have tested it with GCC 5.4.0 and GCC 4.9.4, both of them are ok.
```bash
cd $KM3D_ROOT/src/lib/utiles/iou3d
python setup.py install

