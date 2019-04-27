import sys
import audio_recorder
from glob import glob


def process_wave_files(wave_dir):
    detected_cnt = 0
    results = {}
    for wave_path in glob(wave_dir + "/audio/*.wav"):
        # print("Will process", wave_path)
        _ch_id = int(wave_path.split("/")[-1].split("-")[0])
        results[_ch_id] = audio_recorder.audio_played_second(wave_path, 5)

    for ch_id in sorted(results.keys()):
        result = results[ch_id]
        if result != -1:
            detected_cnt += 1
            print(ch_id, result)
    print("Detected playback in %d of the %d channels via audio." % (
        detected_cnt, len(results)))


if __name__ == '__main__':
    process_wave_files(sys.argv[1])
