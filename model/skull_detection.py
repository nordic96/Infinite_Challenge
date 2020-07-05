import argparse
import http.client
import json
import logger.base_logger

headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Prediction-key': 'a40f5cb7ec74433d90a94820a38eb35f',
}

def detect(img_path, conf):
    data = request_detection(img_path)
    boxes = interpret_result(data, conf)
    return boxes


def request_detection(img):
    try:
        conn = http.client.HTTPSConnection('skull-detection.cognitiveservices.azure.com')
        conn.request("POST", "/customvision/v3.0/Prediction/2cbd63c9-acf6-430a-9ea9-9f5caf06d9d7/detect/iterations/skull_050720/image", img, headers)
        response = conn.getresponse()
        data = response.read()
        data = json.loads(data)
        conn.close()
        return data
    except Exception as e:
        logger.critical("Error connecting to Cognitive Services", e)
        return None


def interpret_result(json_obj, conf):
    boxes = []
    result = json_obj
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
    ap.add_argument("-c", "--cache", type=str, help="cache directory", default="./cache")
    arg = vars(ap.parse_args())
    boxes = detect(arg['input'])
    print(boxes)
