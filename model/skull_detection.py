import argparse
import http.client
import json
import logger.base_logger

headers = {
    # Request headers
    'Content-Type': 'application/octet-stream',
    'Prediction-key': 'a40f5cb7ec74433d90a94820a38eb35f',
}

def request_detection(img_path, cache_path):
    data = open(img_path, 'rb')
    try:
        conn = http.client.HTTPSConnection('skull-detection.cognitiveservices.azure.com')
        conn.request("POST", "/customvision/v3.0/Prediction/2cbd63c9-acf6-430a-9ea9-9f5caf06d9d7/detect/iterations/skull_050720/image", data, headers)
        response = conn.getresponse()
        data = response.read()
        with open(f'{cache_path}/result_cache.json', 'wb') as result:
            result.write(data)
        conn.close()
        return True
    except Exception as e:
        logger.critical("Error connecting to cognitiveservices.azure.com", e)
        return False


def interpret_result(cache_path, conf):
    boxes = []
    with open(f'{cache_path}/result_cache.json') as f:
        result = json.load(f)
        for detection in result['predictions']:
            if detection['probability'] < conf:
                continue
            json_box = detection['boundingBox']
            xywh_box = []
            for coord in json_box:
                xywh_box.append(coord)
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
    request_detection(arg['input'], arg['cache'])
