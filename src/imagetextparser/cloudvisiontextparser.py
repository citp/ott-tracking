import requests
import base64
import os
import json
import argparse
import logging
import io

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

def img_base64(img_file_path):
    img_file = open(img_file_path, 'rb')
    return base64.b64encode(img_file.read())


def make_request(img_file, img_file_base64, key):
    r = requests.post(endpoint % key, data=payload % img_file_base64, headers=headers)

    if r.status_code == 200:
        logger.info('%s successfully queried. Code: %d %s.' % (img_file, r.status_code, requests.status_codes._codes[r.status_code][0]))
        mrjson = json.loads(r.text)
        return mrjson
    else:
        logger.error('%s failed to query. Code: %d %s.' % (img_file, r.status_code, requests.status_codes._codes[r.status_code][0]))
        raise FailedToQueryError()


def compile_text(img_dir, output_dir, key):
    for f in os.listdir(img_dir):
        try:
            output_json = make_request(f, img_base64(os.path.abspath(os.path.join(img_dir, f))), key)

            with io.open(os.path.abspath(os.path.join(output_dir, f + '.json')), 'w', encoding='utf-8') as outfile:
                outfile.write(unicode(json.dumps(output_json, ensure_ascii=False)))
        except:
            logger.exception('Exception while extracting text for %s' % f)
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gets the text in all the image failes in the given directory using the Google Cloud Vision API')
    parser.add_argument('image_dir', help='Folder containing the images')
    parser.add_argument('output_dir', help='Name of the output folder where the results will be dumped')
    parser.add_argument('key', help='Google Cloud API Key')

    args = parser.parse_args()

    img_dir = args.image_dir
    key = args.key
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    compile_text(img_dir, output_dir, key)
