import sys
import audio_recorder
from glob import glob


def process_wave_files(wave_dir):
    results = {}
    for wave_path in glob(wave_dir):
        _ch_id = int(wave_path.split("/")[-1].split("-")[0])
        _result = audio_recorder.audio_played_second(wave_path, 9)
        results[_ch_id] = _result

    for ch_id in sorted(results.keys()):
        result = results[ch_id]
        if result != -1:
            print(ch_id, result)



if __name__ == '__main__':
    process_wave_files(sys.argv[1])
