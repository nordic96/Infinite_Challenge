import os
import ffmpeg
from tqdm import tqdm
from os import listdir, path
import argparse


def convert_avi_to_mp4(avi_file_path, output_name):
    os.popen("ffmpeg -i '{input}' -ac 2 -b:v 2000k -c:a aac -c:v libx264 -b:a 160k -vprofile high -bf 0 -strict "
             "experimental -f mp4 '{output}.mp4'".format(input = avi_file_path, output = output_name))
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="path to input episode files for encodings")
    ap.add_argument("-o", "--output", required=True, help="path to output episode files for encodings")
    args = vars(ap.parse_args())

    vid_dir_path = args['input']
    vid_out_dir_path = args['output']

    for video_path in tqdm(listdir(vid_dir_path)):
        if video_path.lower().endswith('.avi'):
            convert_avi_to_mp4(os.path.join(vid_dir_path, video_path),
                               os.path.join(vid_dir_path, video_path[:-4]))

    for video_path in tqdm(listdir(vid_dir_path)):
        if not video_path.startswith('episode'):
            print('skip ' + video_path)
            continue

        if video_path.endswith('.mp4'):
            vidstream = ffmpeg.input(path.join(vid_dir_path, video_path)).video
            ffmpeg.output(vidstream, path.join(vid_out_dir_path, video_path), vcodec='libx265', crf=30).overwrite_output().run()