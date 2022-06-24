# %%
import subprocess
from pathlib import Path
import cv2

# %% set trial
config = r"C:\Users\jacksonbe3\Box\_Scholarship\research\studentProjects\StinkBugs\maDLCstinkbugs-DLC-2021-01-27\config.yaml"

setf = Path(r"C:\Users\jacksonbe3\Box\_Scholarship\research\studentProjects\StinkBugs\data")
dataf = setf / "20210914" / "set2" / "noL3R3"
run = "cam2_14-Sep-21_20-08-03"

dlcxy = dataf / "pose-2d-filtered" / f"{run}.h5"
newpath = dataf / "videos-raw" / run
vid = dataf / "videos-raw" / f"{run}.mov"
xy = dataf / "videos-raw" / f"{run}-xypts.csv"

# %% convert dlc to dlt for correction
subprocess.run(["python", "dlc2dlt.py", "-config", config, "-dlctracks", dlcxy, "-newpath", newpath, "-offsets", "0", "-like", "0.75", "-vid", vid])

## %% open video in argus
cap = cv2.VideoCapture(str(vid))
end = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
cmd = "C:\\Users\\jacksonbe3\\Miniconda3\\envs\\argus\\python C:\\Users\\jacksonbe3\\Miniconda3\\envs\\argus\\Scripts\\argus-click"
cmd = cmd + f" {str(vid)} {end} 0 1"
subprocess.run(cmd)

# %% Output corrected tracks
subprocess.run(["python", "dlt2dlctracks.py", "-config", config, "-xy", xy, "-dlcxy", dlcxy, "-vid", vid])