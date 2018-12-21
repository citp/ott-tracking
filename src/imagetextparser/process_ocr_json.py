from os.path import join
from glob import glob
import json

JSON_DIR = "../../data/ocr_out"

for json_path in glob(join(JSON_DIR, "*.json")):
    ocr = json.loads(open(json_path).read())
    if not ocr or not len(ocr['responses'][0]):
        continue
    print "*********"
    print "========="
    print "Google Cloud"
    print "========="
    try:
        for txt in ocr['responses'][0]['fullTextAnnotation']['text'].split('\n'):
            if not txt:
                continue
            print txt

    except KeyError:
        print "ERROR", ocr['responses'][0]
    txt_path = json_path.replace("json", "txt")
    print "========="
    print "Tesseract"
    print "========="
    for l in open(txt_path).readlines():
        if not l.strip():
            continue
        print l
    print "========="
