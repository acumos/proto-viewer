#!/usr/bin/env python3
# Acumos - Apache 2.0
# Injects data to proto viewer server
# Data is in dir tests/fixtures

import requests
import random
from time import sleep
from acumos_proto_viewer.utils import _load_module
import sys
import os

def load_proto(model_id):
    """
    Loads a protobuf module and returns it
    """
    expected_path = "tests/fixtures/{0}_pb2.py".format(model_id)
    module = _load_module(model_id, expected_path)
    return module

# generate python modules for each proto file
test = load_proto("probe_testxyz_100_proto")
test2 = load_proto("probe_testimage_100_proto")
ARRAY_TEST = load_proto("image_mood_classification_100_proto")

HOST = "localhost:5006" #default
if len(sys.argv) > 1:
    HOST = sys.argv[1]
print("Fake Data Target Host: {0}".format(HOST))
url = "http://{0}/data".format(HOST)

# well-known proto files are fetched from this server
NEXUS = os.environ["NEXUSENDPOINTURL"]

X = 0
while True:
    for i in range(0, 5): #fire 5x as much fake XYZ as images
        X += 1
        msg = test.XYZData()
        msg.x = X
        msg.y = random.randint(0, 10)
        msg.z = random.randint(50, 100)
        msgb = msg.SerializeToString()
        try:
            r = requests.post(url,
                              data=msgb,
                              headers={"PROTO-URL": "{0}/probe-testxyz-100.proto".format(NEXUS),
                                       "Message-Name": "XYZData"})
            print("Testxyz: status code: {0}".format(r.status_code))
            assert(msgb == r.content)
            sleep(0.1)
        except requests.exceptions.ConnectionError: #allow this script to keep running when developing and shutting on/off the server
            pass

    #try a test with arrays
    new_dict = {}
    for listKey in ['good', 'bad', 'ugly', 'very good', 'very bad', 'very ugly', 'beautiful', 'horrid', 'amazing', 'terrible']:
        new_dict[listKey] = random.random()
    msg1 = ARRAY_TEST.ImageTagSet(image = [0,1,2,3,4,5,6,7,8,9], tag=list(new_dict.keys()), score=list(new_dict.values()))
    msg1b = msg1.SerializeToString()
    try:
        r = requests.post(url,
                          data=msg1b,
                          headers={"PROTO-URL": "{0}/image-mood-classification-100.proto".format(NEXUS),
                                   "Message-Name": "ImageTagSet"})
        print("Img-mood-class: status code: {0}".format(r.status_code))
        assert(msg1b == r.content)
    except requests.exceptions.ConnectionError: #allow this script to keep running when developing and shutting on/off the server
        pass

    msg2 = test2.TransformedImagePNG()
    theimage = random.choice(["1.png","2.png","3.png","4.png","5.png","6.png","7.png","8.png","9.png","10.png"])
    # expects to be called with CWD of project base
    thefile = "tests/fixtures/{0}".format(theimage)
    ib = open(thefile, "rb").read()
    msg2.imagebinary = ib
    msg2b = msg2.SerializeToString()
    try:
        r = requests.post(url,
                          data=msg2b,
                          headers={"PROTO-URL": "{0}/probe-testimage-100.proto".format(NEXUS),
                                   "Message-Name": "TransformedImagePNG"})
        print("probe test img png: status code: {0}".format(r.status_code))
        assert(msg2b == r.content)
    except requests.exceptions.ConnectionError:
        pass

    msg3 = test2.TransformedImageJPEG()
    theimage = random.choice(["1j.jpg","2j.jpg","3j.jpg","4j.jpg", "5j.jpg", "6j.jpg"])
    # expects to be called with CWD of project base
    thefile = "tests/fixtures/{0}".format(theimage)
    ib = open(thefile, "rb").read()
    msg3.imagebinary = ib
    msg3b = msg3.SerializeToString()
    try:
        r = requests.post(url,
                          data=msg3b,
                          headers={"PROTO-URL": "{0}/probe-testimage-100.proto".format(NEXUS),
                                   "Message-Name": "TransformedImageJPEG"})
        print("probe test img jpg: status code: {0}".format(r.status_code))
        assert(msg3b == r.content)
    except requests.exceptions.ConnectionError:
        pass

    sleep(.5)
