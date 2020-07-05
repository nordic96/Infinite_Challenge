import argparse
import http.client
import json
from logger.base_logger import logger

headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Prediction-key': 'a40f5cb7ec74433d90a94820a38eb35f',
}

def detect(img, conf, config):
    model_version = config.get("SKULL", "model_version")
    data = request_detection(img, model_version)
    boxes = interpret_result(data, conf)
    return boxes


def request_detection(img, model_version):
    try:
        conn = http.client.HTTPSConnection('skull-detection.cognitiveservices.azure.com')
        conn.request("POST", f'/customvision/v3.0/Prediction/2cbd63c9-acf6-430a-9ea9-9f5caf06d9d7/detect/iterations/{model_version}/image', img, headers)
        response = conn.getresponse()
        data = response.read()
        data = json.loads(data)
        conn.close()
        return data
    except Exception as e:
        logger.critical("Error connecting to Cognitive Services", e)
        raise e


def interpret_result(result, conf):
    boxes = []
    for detection in result['predictions']:
        if detection['probability'] < conf:
            continue
        json_box = detection['boundingBox']
        xywh_box = [json_box['left'], json_box['top'], json_box['width'], json_box['height']]
        boxes.append(xywh_to_yxyx(xywh_box))
    return boxes


def xywh_to_yxyx(orig_box):
    assert len(orig_box) == 4
    x2 = orig_box[0]
    x1 = x2 + orig_box[2]
    y1 = orig_box[1]
    y2 = y1 + orig_box[3]
    return [y1, x1, y2, x2]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, type=str, help="path to image")
    arg = vars(ap.parse_args())
    boxes = detect(arg['input'])
    print(boxes)
