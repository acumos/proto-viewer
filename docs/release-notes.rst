.. ===============LICENSE_START=======================================================
.. Acumos CC-BY-4.0
.. ===================================================================================
.. Copyright (C) 2017-2018 AT&T Intellectual Property & Tech Mahindra. All rights reserved.
.. ===================================================================================
.. This Acumos documentation file is distributed by AT&T and Tech Mahindra
.. under the Creative Commons Attribution 4.0 International License (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
.. http://creativecommons.org/licenses/by/4.0
..
.. This file is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.
.. ===============LICENSE_END=========================================================

==========================
Proto Viewer Release Notes
==========================

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <http://keepachangelog.com/>`__
and this project adheres to `Semantic Versioning <http://semver.org/>`__.

[1.5.2] - 6/29/2018
-------------------

- Add debug logging statements to util functions

[1.5.1] - 6/11/18
-----------------

- Change "recieved" to "received" in probe's metadata key

[1.5.0] - 4/24/18
-----------------

- Add table option to view data in rows and columns

[1.4.2] - 3/25/18
-----------------

- Make raw formatting work even with bytes by truncating them

[1.4.1] - 3/25/18
-----------------

- Slightly better raw formatting

[1.4.0] - 3/25/18
-----------------

- Handle "repeated" keyword
- Better raw display

[1.3.1] - 3/24/18
-----------------

- Swap out marshal for pickle

[1.3.0]
-------

- No longer need NGINX

[1.2.0]
-------

-  Makes the probe compatible with ONAP Message Router
-  Code cleanups, increase in testing, use better concepts in bin/run

[1.1.0]
-------

-  Allow the POST to contain a partial URL, and implement the ENV
   variable the model connector will deploy the probe with;
   contatenating the two forms the full probe URL.
-  Start the breakout of functionality from bin/run to other modules to
   enable more unit testing
-  Fix more (but not all) pylint violations

[1.0.0]
-------

-  Move from modelid to protourl, and rename headers per what model
   connector wants
-  Probe will now download the proto file from the URL
-  Fix some PEP8 violations after installing FLAKE8

[0.7.0]
-------

-  By request from Kazi, when posting into /data, return the request
   body back to the caller.

[0.6.0]
-------

-  Switch to Redis so we can start TTLing datasets
-  Add tests

[0.5.0]
-------

-  Move to NGINX reverse proxy to get rid of hostname nonsense
-  Add target host as a cmd line arg in ``fake_data``

[0.4.0]
-------

-  Package my own image resolver to drastically shrink page size; data
   URLs are huge

[0.3.0]
-------

-  Code cleanups; move get_raw_index into a get/setter abstraction
   instead
-  Support JPEG, make user select MIME type instead of assuming PNG
-  Rename POST /senddata to POST /data to be “rest-ier”

[0.2.0]
-------

-  Add UPDATE_CALLBACK_FREQUENCY as an env variable
-  Add ``apv_model_as_string`` to each record
-  Add ``apv_sequence_number`` to each record
-  Add a ``raw`` type; still needs astetic work

[0.1.0]
-------

-  Dockerize
-  Switch from gunicorn to Tornado

[0.0.5]
-------

-  Inject timestamp into all incoming records
-  Switch graph selection and field selection
-  Support image type (most of this PRs work)
-  Bugfixes, cleanups.

[0.0.4]
-------

-  Switch to a third party lib for parsing the proto file
-  Move away from the proto file name being significant, to a notion of
   "model id" instead
-  Support multiple connections

[0.0.3]
-------

-  This changelog started
-  Add input controls for selection proto file etc
-  Add util functions for listing and loading compiled protos
-  Added Paul’s code for parsing proto file
