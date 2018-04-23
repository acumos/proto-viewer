#!/usr/bin/env python3
# Acumos - Apache 2.0
# Injects data to proto viewer server from files in /tmp;
# the data files include images so are not in git.

import requests
import random
from time import sleep
from acumos_proto_viewer.utils import load_proto
import sys
import os

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
                              headers={"PROTO-URL": "{0}/probe_testxyz/1.0.0/probe_testxyz-1.0.0-proto".format(NEXUS),
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
                          headers={"PROTO-URL": "{0}/image-mood-classification/1.0.0/image-mood-classification-1.0.0-proto".format(NEXUS),
                                   "Message-Name": "ImageTagSet"})
        print("Img-mood-class: status code: {0}".format(r.status_code))
        assert(msg1b == r.content)
    except requests.exceptions.ConnectionError: #allow this script to keep running when developing and shutting on/off the server
        pass

    msg2 = test2.TransformedImagePNG()
    theimage = random.choice(["/tmp/1.png","/tmp/2.png","/tmp/3.png","/tmp/4.png","/tmp/5.png","/tmp/6.png","/tmp/7.png","/tmp/8.png","/tmp/9.png","/tmp/10.png"])
    ib = open(theimage, "rb").read()
    msg2.imagebinary = ib
    msg2b = msg2.SerializeToString()
    try:
        r = requests.post(url,
                          data=msg2b,
                          headers={"PROTO-URL": "{0}/probe_testimage/1.0.0/probe_testimage-1.0.0-proto".format(NEXUS),
                                   "Message-Name": "TransformedImagePNG"})
        print("probe test img png: status code: {0}".format(r.status_code))
        assert(msg2b == r.content)
    except requests.exceptions.ConnectionError:
        pass

    msg3 = test2.TransformedImageJPEG()
    theimage = random.choice(["/tmp/1j.jpg","/tmp/2j.jpg","/tmp/3j.jpg","/tmp/4j.jpg", "/tmp/5j.jpg", "/tmp/6j.jpg"])
    ib = open(theimage, "rb").read()
    msg3.imagebinary = ib
    msg3b = msg3.SerializeToString()
    try:
        r = requests.post(url,
                          data=msg3b,
                          headers={"PROTO-URL": "{0}/probe_testimage/1.0.0/probe_testimage-1.0.0-proto".format(NEXUS),
                                   "Message-Name": "TransformedImageJPEG"})
        print("probe test img jpg: status code: {0}".format(r.status_code))
        assert(msg3b == r.content)
    except requests.exceptions.ConnectionError:
        pass

    sleep(.5)
