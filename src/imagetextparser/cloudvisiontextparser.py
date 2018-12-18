import requests
import base64
import os
import json
import argparse

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

def make_request(img_file_base64, key):
    r = requests.post(endpoint % key, data=payload % img_file_base64, headers=headers)

    if r.status_code == 200:
        mrjson = json.loads(r.text)
        return mrjson['responses'][0]['fullTextAnnotation']['text']

def compile_text(img_dir, key):
    for f in os.listdir(img_dir):
        make_request(img_base64(os.path.abspath(os.path.join(img_dir, f))), key)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gets the text in all the images in the given directory using the Google Cloud Vision API')
    parser.add_argument('image_dir', help='Folder containing the images')
    parser.add_argument('key', help='Google Cloud API Key')
    parser.add_argument('output', help='Name of the output CSV file')

    args = parser.parse_args()

    img_dir = args.image_dir
    key = args.key

    compile_text(img_dir, key)
