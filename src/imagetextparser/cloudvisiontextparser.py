import requests
import base64
import os
import json
import argparse
import logging
import io
from os.path import join, basename, abspath
from glob import glob
from _collections import defaultdict
import binascii
import pytesseract
from celery import Celery


class FailedToQueryError(Exception):
    '''Cloud API returned non 200 status code'''
    pass


logger = logging.getLogger(__name__)
lf_handler = logging.FileHandler('text_extraction.log')
lf_format = logging.Formatter('%(asctime)s - %(message)s')
lf_handler.setFormatter(lf_format)
logger.addHandler(lf_handler)
logger.setLevel(logging.INFO)

payload = '''{
  'requests': [
    {
      'image': {
        'content': '%s'
      },
      'features': [
        {
          'type': 'TEXT_DETECTION'
        }
      ]
    }
  ]
}'''

headers = {'Content-Type': 'application/json; charset=utf-8'}
endpoint = 'https://vision.googleapis.com/v1/images:annotate?key=%s'


FILTER_TEXTLESS_IMGS_USING_TESSERACT = True


def get_img_base64(img_file_path):
    img_file = open(img_file_path, 'rb')
    return base64.b64encode(img_file.read())


app = Celery('cloudvisiontextparser', broker='pyamqp://guest@localhost//')


@app.task
def call_make_request(img_path, img_base64, key, output_dir):
    try:
        img_basename = basename(img_path)
        json_str = make_request(img_path, img_base64, key)
        json_path = join(output_dir, img_basename + '.json')
        with io.open(abspath(json_path), 'w', encoding='utf-8') as f:
            f.write(unicode(json.dumps(json_str, ensure_ascii=False)))
    except Exception:
        logger.exception(
            'Exception while extracting text for %s' % img_basename)


def make_request(img_file, img_file_base64, key):
    r = requests.post(endpoint % key, data=payload % img_file_base64,
                      headers=headers)

    if r.status_code == 200:
        logger.info('%s successfully queried. Code: %d %s.' % (
            img_file, r.status_code,
            requests.status_codes._codes[r.status_code][0]))
        mrjson = json.loads(r.text)
        return mrjson
    else:
        logger.error('%s failed to query. Code: %d %s.' % (
            img_file, r.status_code,
            requests.status_codes._codes[r.status_code][0]))
        raise FailedToQueryError()


def compile_text(img_dir, output_dir, key):
    # for f in os.listdir(img_dir):
    channel_crcs = defaultdict(set)  # set of image checksums seen
    for img_path in sorted(glob(join(img_dir, '*.png'))):
        img_basename = basename(img_path)
        channel_id = img_basename.split("-")[0]
        img_base64 = get_img_base64(img_path)
        img_crc32 = binascii.crc32(img_base64)

        if img_crc32 in channel_crcs[channel_id]:
            logger.info(
                "Image seen before, will skip API call %s" % img_basename)
            continue
        channel_crcs[channel_id].add(img_crc32)

        if FILTER_TEXTLESS_IMGS_USING_TESSERACT:
            text = pytesseract.image_to_string(img_path, lang='eng')
            if not text:
                logger.info(
                    "Image doesn't contain text (by tesseract) %s, will skip."
                    % img_basename)
                continue
            txt_path = join(output_dir, img_basename + '.txt')
            with io.open(abspath(txt_path), 'w', encoding='utf-8') as f:
                f.write(text)

        logger.info("Will run text recognition %s" % img_basename)
        call_make_request.delay(img_path, img_base64, key, output_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Gets the text in all the image files in the given"
        " directory using the Google Cloud Vision API")
    parser.add_argument('image_dir', help='Folder containing the images')
    parser.add_argument(
        'output_dir',
        help='Name of the output folder where the results will be dumped')
    parser.add_argument('key', help='Google Cloud API Key')

    args = parser.parse_args()

    img_dir = args.image_dir
    key = args.key
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    compile_text(img_dir, output_dir, key)
