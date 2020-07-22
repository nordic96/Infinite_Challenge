import http.client
import json
from infinitechallenge.logging import logger


def headers_with_prediction_key(key):
    assert len(key) > 0
    if len(key) == 0:
        raise ValueError('Prediction Key must be specified')
    return {
        # Request headers
        'Content-Type': 'application/octet-stream',
        'Prediction-key': key
    }


def detect(img, key, confidence, model_version):
    data = request_detection(img, model_version, key)
    boxes = interpret_result(data, confidence)
    return boxes


def request_detection(img, model_version, key):
    try:
        conn = http.client.HTTPSConnection('skull-detection-sea.cognitiveservices.azure.com')
        headers = headers_with_prediction_key(key)
        conn.request("POST", f'/customvision/v3.0/Prediction/ae33224a-a67d-4489-bd07-a4405035700f/detect/iterations/{model_version}/image', img, headers)
        response = conn.getresponse()
        data = response.read()
        data = json.loads(data)
        conn.close()
        return data
    except Exception as e:
        logger.critical("Error connecting to Cognitive Services:", e)
        raise e


def interpret_result(result, conf):
    boxes = []
    try:
        for detection in result['predictions']:
            if detection['probability'] < conf:
                continue
            if detection['tagName'] != 'skull':
                continue
            json_box = detection['boundingBox']
            xywh_box = [json_box['left'], json_box['top'], json_box['width'], json_box['height']]
            boxes.append(xywh_to_yxyx(xywh_box))
        return boxes
    except Exception as e:
        logger.critical("Bad response:", e)
        raise e


def xywh_to_yxyx(orig_box):
    assert len(orig_box) == 4
    x2 = orig_box[0]
    x1 = x2 + orig_box[2]
    y1 = orig_box[1]
    y2 = y1 + orig_box[3]
    return [y1, x1, y2, x2]
