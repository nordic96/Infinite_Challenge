import os
import sys
import math
from src.logging.result_logger import logger
sys.path.append(os.getcwd())


def _average_coordinate(list_of_coordinates):
    sum_x = 0.0
    sum_y = 0.0
    for x, y in list_of_coordinates:
        sum_x += x
        sum_y += y
    return (sum_x / len(list_of_coordinates)), (sum_y / len(list_of_coordinates))


def _bounding_box_centre(bounding_box):
    t,l,b,r = bounding_box
    return (t+b)/2.0, (l+r)/2.0


def _euclidian_distance(pt1, pt2):
    return pow(pow(pt1[0]+pt2[1], 2) + pow(pt1[1]+pt2[1], 2), 0.5)


def estimate_burned_member(skull_bounding_boxes, face_bounding_boxes, names):
    if not skull_bounding_boxes or not face_bounding_boxes:
        return None

    # calculate average skull coordinate
    skull_midpts = list(map(_bounding_box_centre, skull_bounding_boxes))
    skull_avg = _average_coordinate(skull_midpts)

    # calculate closest member to skull avg coordinate
    burned_member = None
    closest = math.inf
    for bounding_box, name in zip(face_bounding_boxes, names):
        face_centre = _bounding_box_centre(bounding_box)
        dist = _euclidian_distance(face_centre, skull_avg)
        if dist < closest:
            burned_member = name
            closest = dist
        elif dist == closest:
            if name != burned_member and name == 'unknown':
                logger.warning(f'Both {name} and {burned_member} are both equally close '
                               f'to the average skull coordinate, discarding {name}...')
            elif name != burned_member and burned_member == 'unknown':
                logger.warning(f'Both {name} and {burned_member} are both equally close '
                               f'to the average skull coordinate, discarding {burned_member}...')
                burned_member = name

    return burned_member
