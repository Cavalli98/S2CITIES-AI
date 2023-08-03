# S2CITIES-AI
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

Video-based Recognition of the "The Canadian Women's Foundation" Signal for Help

## Installation

1. Clone this repository with `git clone https://github.com/S2CITIES/S2CITIES-AI`
2. Install the dependencies with `pip install -r requirements.txt`

## Usage

1. Follow the istructions to have the [`4_videos_labeled`](./src/dataset_creation/4_videos_labeled/) folder with the labeled videos:
   1. Run the script [`dataset_creation_move_and_split.py`](./dataset_creation_move_and_split.py) to move, rename and split the videos.
   2. Run the script [`dataset_creation_starter_csv.py`](./dataset_creation_starter_csv.py) to create the starter CSV file and facilitate labeling by someone else.
   3. Run the script [`dataset_creation_perform_labeling.py`](./dataset_creation_perform_labeling.py) to actually perform the labeling.
   4. Run the script [`dataset_creation_move_labeled.py`](./dataset_creation_move_labeled.py) to move the labeled videos into the respective class folders according to the CSV file.
2. Run the script [`dataset_creation_subsample_videos.py`](./dataset_creation_subsample_videos.py) to subsample the videos to a predefined FPS
3. [WIP] Run the script [`extract_features.py`](./src/extract_features.py) to extract the keypoints using MediaPipe
4. [WIP] Run the script [`timeseries_feature_extraction.py`](./src/timeseries_feature_extraction.py) to extract features from the timeseries of keypoints using, momentarily, [`tsfresh`](https://tsfresh.readthedocs.io/)
5. Run the [`train_model_nn.py`](./train_model_nn.py) or the [`train_model_stats.py`](./train_model_stats.py) to train the model for classification.

## Installing TensorFlow + MediaPipe on Apple Silicon

**DEPRECATED**: This is probably not needed anymore, since the latest version of MediaPipe now supports macOS natively.

1. ~~Install `pip install mediapipe-silicon` which installs `protobuf==3.20.3`.~~
2. ~~Take the `builder.py` from the installed version and copy it somewhere else `~/.pyenv/versions/s2cities/lib/python3.10/site-packages/google/protobuf/internal`.~~
3. ~~Install `pip install tensorflow-macos tensorflow-metal` which installs `protobuf==3.19.6`. TensorFlow has priority, so keep this version, but overwrite the `builder.py` with the one you took earlier.~~

https://stackoverflow.com/questions/71759248/importerror-cannot-import-name-builder-from-google-protobuf-internal

## Resources

### Mediapipe

- https://mediapipe-studio.webapps.google.com/demo/hand_landmarker
- https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
- https://developers.google.com/mediapipe/solutions/vision/hand_landmarker/python#image
- https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb#scrollTo=_JVO3rvPD4RN

### General computer vision

- [Advanced Computer Vision with Python - Full Course](https://www.youtube.com/watch?v=01sAkU_NvOY)
- [CS231n Winter 2016: Lecture 14: Videos and Unsupervised Learning](https://www.youtube.com/watch?v=ekyBklxwQMU)
- [OpenPose](https://github.com/CMU-Perceptual-Computing-Lab/openpose) (too hard)

## Authors

- Teo Bucci ([@teobucci](https://github.com/teobucci))
- Dario Cavalli ([@Cavalli98](https://github.com/Cavalli98))
- Giuseppe Stracquadanio ([@pestrstr](https://github.com/pestrstr))
