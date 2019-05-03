import json
import sys
import audio_recorder
from glob import glob
from os.path import basename, join, isdir


def process_wave_files(crawl_dir, dump_results=False):
    detected_cnt = 0
    results = {}
    if dump_results:
        post_process_dir = join(crawl_dir, 'post-process')
        assert isdir(post_process_dir)
        out_json = join(post_process_dir, 'playback-detection.json')

    for wave_path in glob(crawl_dir + "/audio/*.wav"):
        _ch_name = basename(wave_path).rsplit("-", 1)[0]
        results[_ch_name] = audio_recorder.audio_played_second(wave_path, 5)

    if dump_results:
        with open(out_json, 'w') as f:
            json.dump(results, f)
        print("Playback detection results written to %s" % out_json)
    else:
        for _ch_name in sorted(results.keys()):
            detection_time = results[_ch_name]
            if detection_time != -1:
                detected_cnt += 1
                print(_ch_name, detection_time)
        print("Detected playback in %d of the %d channels via audio." % (
            detected_cnt, len(results)))
    return results


"""
Usage:
    - To print results: python3 detect_audio.py crawl_dir
    - To dump results as json: python3 detect_audio.py crawl_dir --dump
"""

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == '--dump':
        process_wave_files(sys.argv[1], True)
    else:
        process_wave_files(sys.argv[1])
