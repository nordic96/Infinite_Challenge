import re


def get_episode_number_from_filename(episode_filename):
    EPISODE_FILENAME_PATTERN = '^episode(\d+)[.]\w+$'
    parsed = re.findall(EPISODE_FILENAME_PATTERN, episode_filename, re.IGNORECASE)
    if len(parsed) != 1:
        raise Exception(f'Episode filename does not match pattern: {EPISODE_FILENAME_PATTERN}')
    episode_num = parsed[0]
    return episode_num
