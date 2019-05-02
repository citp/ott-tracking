import sys
import audio_recorder
from glob import glob
from os.path import basename


def process_wave_files(wave_dir):
    detected_cnt = 0
    results = {}
    for wave_path in glob(wave_dir + "/audio/*.wav"):
        wave_name = basename(wave_path)
        # print("Will process", wave_path)
        _ch_name = wave_name.rsplit("-", 1)[0]
        # print(_ch_name, wave_path)
        results[_ch_name] = audio_recorder.audio_played_second(wave_path, 5)

    for _ch_name in sorted(results.keys()):
        result = results[_ch_name]
        if result != -1:
            detected_cnt += 1
            print(_ch_name, result)
    print("Detected playback in %d of the %d channels via audio." % (
        detected_cnt, len(results)))


if __name__ == '__main__':
    process_wave_files(sys.argv[1])
