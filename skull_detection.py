import subprocess

YOLOV5_PATH = './dataset/skull/yolov5/'
IMAGE_NUM = 10
CONFIDENCE = 0.7

subprocess.call(['pip', 'install', '-r', f'{YOLOV5_PATH}requirements.txt']) # setup yolov5 environment
print("setup complete")

subprocess.call(['python', f'{YOLOV5_PATH}detect.py', '--weights', f"{YOLOV5_PATH}weights/last_yolov5s_results.pt",
                 '--img', f"{IMAGE_NUM}", '--conf', f"{CONFIDENCE}", '--source', "./dataset/skull/test_infer"])
