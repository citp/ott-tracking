import requests
import base64
import os
import json
import argparse
import logging

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
        mrjson = json.loads(r.text)
        logger.info('%s successfully queried. Code: %d %s.' % (img_file, r.status_code, requests.status_codes._codes[r.status_code][0]))
        return mrjson['responses'][0]['fullTextAnnotation']['text']
    else:
        logger.error('%s failed to query. Code: %d %s.' % (img_file, r.status_code, requests.status_codes._codes[r.status_code][0]))
        raise FailedToQueryError()


def compile_text(img_dir, writer, key):
    for f in os.listdir(img_dir):
        try:
            text_content = make_request(f, img_base64(os.path.abspath(os.path.join(img_dir, f))), key)
            writer.write(f + ',' + repr(text_content.encode('utf8')) + '\n')
        except:
            logger.exception('Exception while extracting text for %s' % f)
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gets the text in all the image failes in the given directory using the Google Cloud Vision API')
    parser.add_argument('image_dir', help='Folder containing the images')
    parser.add_argument('output_file', help='Name of the output CSV file')
    parser.add_argument('key', help='Google Cloud API Key')

    args = parser.parse_args()

    img_dir = args.image_dir
    key = args.key
    output_file = args.output_file

    writer = open(output_file, 'w')

    writer.write('file,text\n')
    compile_text(img_dir, writer, key)
