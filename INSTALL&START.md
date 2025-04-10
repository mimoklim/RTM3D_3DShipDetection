The code was tested on Ubuntu 16.04, with Anaconda Python 3.6 and PyTorch v1.0.0. NVIDIA GPUs are needed for both training and testing. To replicate the environment, we containerized the setup using a Docker image, making it easier to manage dependencies and ensure reproducibility.

```markdown
<INSTALL>

- Compile deformable convolutional (from DCNv2).
```bash
# git clone https://github.com/CharlesShang/DCNv2/
cd $RTM3D_3DShipDetection/src/lib/models/networks/
cd DCNv2
./make.sh
```
  
- Compile iou3d (from pointRCNN). GCC>4.9, I have tested it with GCC 5.4.0 and GCC 4.9.4, both of them are ok.
```bash
cd $RTM3D_3DShipDetection/src/lib/utiles/iou3d
python setup.py install
```

<START>

Training & Testing & Evaluation
- Training by python with multiple GPUs in a machine
Run following command to train model with ResNet-18 backbone.
```bash
python ./src/main.py --data_dir ./kitti_format --exp_id KM3D_res18 --arch res_18 --batch_size 32 --master_batch_size 16 --lr 1.25e-4 --gpus 0,1 --num_epochs 200
```
Run following command to train model with DLA-34 backbone.
```bash
python ./src/main.py --data_dir ./kitti_format --exp_id KM3D_dla34 --arch dla_34 --batch_size 16 --master_batch_size 8 --lr 1.25e-4 --gpus 0,1 --num_epochs 200
```

Visualization
Run following command for visualization.
```bash
# ResNet-18 backbone
python ./src/faster.py --vis --demo ./kitti_format/data/kitti/val.txt --data_dir ./kitti_format --calib_dir ./kitti_format/data/kitti/calib/ --load_model ./kitti_format/exp/KM3D_res18/model_last.pth --gpus 0 --arch res_18
# or DLA-3D backbone
python ./src/faster.py --vis --demo ./kitti_format/data/kitti/val.txt --data_dir ./kitti_format --calib_dir ./kitti_format/data/kitti/calib/ --load_model ./kitti_format/exp/KM3D_dla34/model_last.pth --gpus 0 --arch res_18
```

Evaluation
Run following command for evaluation.
```bash
python ./src/tools/kitti-object-eval-python/evaluate.py evaluate --label_path=./kitti_format/data/kitti/label/ --label_split_file ./ImageSets/val.txt --current_class=0,1,2 --coco=False --result_path=./kitti_format/exp/results/data/
```
