import time
from pathlib import Path
import os
import cv2
import json
import pandas as pd

from utils import get_video_files, move_file

class VideoLabeler:
    def __init__(self, const_file_path):
        # Read from json file
        with open(const_file_path, "r", encoding="utf-8") as f:
            const = json.load(f)

        self.VIDEO_EXTENSIONS = tuple(const["VIDEO_EXTENSIONS"])

        self.VIDEOS_LABEL_0_FOLDER = Path(const["VIDEOS_LABELED"]) / "0"
        self.VIDEOS_LABEL_1_FOLDER = Path(const["VIDEOS_LABELED"]) / "1"
    
    def read_dataframe(self, csv_filename):
        # Read from csv file
        self.dataframe = pd.read_csv(csv_filename)
        

    def label_videos(self, source_folder):

        # Iterate over the dataframe
        for index, video in self.dataframe.iterrows():
            
            # Skip if video is already processed
            # i.e. if the label has already been set to either 0 or 1
            if not video["label"] == -1:
                continue

            file_path = os.path.join(source_folder, video["file"])
            
            cap = cv2.VideoCapture(file_path)

            while cap.isOpened():
                ret, frame = cap.read()

                if not ret:
                    time.sleep(1)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                cv2.imshow('Video Player', frame)
                key = cv2.waitKey(1) & 0xFF

                if key == ord('1'):
                    # Set label to 1
                    print(f"Labeling video {video['file']} as 1")
                    self.dataframe.at[index, "label"] = 1
                    break
                elif key == ord('0'):
                    # Set label to 0
                    print(f"Labeling video {video['file']} as 0")
                    self.dataframe.at[index, "label"] = 0
                    break
                elif key == ord('q'):
                    return

            cap.release()
            cv2.destroyAllWindows()

    def update_csv(self, csv_filename):
        self.dataframe.to_csv(csv_filename, index=False)

    def create_starter_csv(self, folder, csv_filename):
        video_files = get_video_files(folder, self.VIDEO_EXTENSIONS)
        video_info = [{"file": file, "label": -1} for file in video_files]
        df = pd.DataFrame(video_info)
        # Sort by file name
        #df = df.sort_values(by=["file"])
        df.to_csv(csv_filename, index=False)
    
    # Read the csv and move files to the corresponding folder based on the label
    def move_files(self, source_folder):
        # Create folders if they don't exist
        self.VIDEOS_LABEL_0_FOLDER.mkdir(parents=True, exist_ok=True)
        self.VIDEOS_LABEL_1_FOLDER.mkdir(parents=True, exist_ok=True)
        for index, video in self.dataframe.iterrows():
            if video["label"] == 1:
                move_file(str(Path(source_folder) / video['file']), str(self.VIDEOS_LABEL_1_FOLDER / video['file']))
            elif video["label"] == 0:
                move_file(str(Path(source_folder) / video['file']), str(self.VIDEOS_LABEL_0_FOLDER / video['file']))
            else:
                print("File {} has no label".format(video["file"]))