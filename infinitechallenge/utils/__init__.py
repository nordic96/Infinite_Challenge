import os
import sys
from PIL import Image, ImageDraw
sys.path.append(os.getcwd())


def label_image(src_path, dst_path, label_list):
    """
    :param src_path: path of image to label
    :param dst_path: destination path to save labelled image
    :param label_list: List of (label, (top, left, bottom, right), color) tuples
    """
    img = Image.open(src_path)
    draw = ImageDraw.Draw(img)
    for (label, (top, left, bottom, right), color) in label_list:
        rect = (left, top), (right, bottom)
        # draw box
        draw.rectangle(rect, outline=color, width=4)
        # label box
        w, h = draw.textsize(label)
        background_rect = (left, bottom), (left + w, bottom + h)
        draw.rectangle(background_rect, fill=color)
        draw.text((left, bottom), label)
    img.save(dst_path)
