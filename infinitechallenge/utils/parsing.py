import re


def get_episode_number(episode_filename, filename_pattern):
    parsed = re.findall(filename_pattern, episode_filename, re.IGNORECASE)
    if len(parsed) != 1:
        raise Exception(f'Episode filename does not match pattern: {filename_pattern}')
    episode_num, file_ext = parsed[0]
    return episode_num
