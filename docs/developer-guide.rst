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
..      http://creativecommons.org/licenses/by/4.0
..
.. This file is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.
.. ===============LICENSE_END=========================================================

============================
Proto Viewer Developer Guide
============================

This project allows visualization of data being transferred in protobuf format.
Probing a specific message requires access to the corresponding protocol buffer
definition (.proto) file on an external network server, usually a Nexus registry.

Development Quickstart
======================

The following steps set up a development environment without use of Docker.

0. Install prerequisites locally so they can be invoked by the probe:

    a. The protocol buffer compiler ("protoc"), version 3.5 or later
    b. The protobuf-jsonschema tool, version 1.1.1 or later

1. Obtain the set of test data (messages and image files) from the original developer and unpack to the /tmp directory.  You should have a file /tmp/1.png and so on.

2. Download and build the redis server on the development machine, then start it:

    https://redis.io/download

    src/redis-server --daemonize yes

3. Clone the proto-viewer repository::

    git clone https://gerrit.acumos.org/r/proto-viewer

4. Create a virtual environment with Python 3.6 (version 3.5 may not work, use 3.6) locally::

    virtualenv -p python3.6 apv36

5. Use the virtual environment to install this package::

    ./apv36/bin/pip install -r requirements.txt
    ./apv36/bin/pip install .

6. Set an environment variable with the URL of the Nexus server that has the required protobuf files::

    export NEXUSENDPOINTURL=http://nexus.domain.com/repository/repo

7. Launch the Bokeh-enabled web server::

    ./apv36/bin/python3 bin/run.py

8. Start the data-injection script::

    ./apv36/bin/python3 fake_data.py

Dependencies
============

If you are running in Docker, there are no external dependencies, it is,
for better or worse[1], totally self contained.

If you are running locally, you will need to have :
1. redis running on the standard port, reachable from **localhost**
2. you will also need an `npm` package: `npm install protobuf-jsonschema`.

[1] This Docker container runs Nginx, Redis, and Bokeh. At one point I was told the probe had to be a single Docker container.

Data Retention
==============

The current server side (probe) data retention policy is that the raw
data cache resets every midnight. Meaning, if a user logs into the
probe, they will see all data that came in since the prior midnight, and
will see new data as it streams in. This is because the probe may be a
long running process, and memory would increase without bound, so the
probe has to have a TTL on data. If there is a need for a user to log in
and see MORE data than the prior midnight, we can change this later by
increasing the TTL to the last week or something.

For the client side, Bokeh has a notion of a DataSource per session,
which holds the data sent from the server to the browser, so we also
have to limit the client side data, in case a user is logged in for a
very long time. The “streaming limit” for numerical data is 100,000
records, just over a day of data assuming one record per second. The
streaming limit for images and raw data is just 1; the user sees it as
it goes by, or it is lost (there is currently no replay).

Filesystem
==========

This application makes the directory **/tmp/protofiles** and uses that
for the proto files. Inside Docker this all gets cleaned up. On your
machine if you run this, be sure to clean that after. Note many OSs
automatically clean up **/tmp** on reboot.

Build
=====

.. code:: bash

    docker build -t YOURREG:18443/acumos_proto_viewer:1.0.0 .
    docker push YOURREG:18443/acumos_proto_viewer:1.0.0

Run
===

.. code:: bash

    docker run -dit -p 80:80 YOURREG:18443/acumos_proto_viewer:1.0.0


Optional additional env variables
---------------------------------

You can also pass in the following to alter the run behavior:

1. UPDATE_CALLBACK_FREQUENCY // sets the frequency, in ms (1000=every
   second) of the callbacks that update the graphs on the screen, e.g.,


Fake data
=========

To launch a script that generates fake data and sends it:

.. code:: bash

    fake_data.py [host:port]

**[host:port]** is an optional cmd line argument giving the target proto
to send data to; it defaults to **localhost:5006** for local
development.

Extra Fields
============

Every protobuf message that enters the **/senddata** endpoint is
injected, by this server, with additional keys:

1. **apv_received_at**: the epoch timestamp that the model was received
   at. Used for plotting a single variable against time
2. **apv_model_as_string**: the string representation of the entire
   model, used for plotting the raw text if the user chooses
3. **apv_sequence_number**: the sequence number of this “type” of raw
   data, where type = (model_id, message_name)