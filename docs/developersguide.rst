.. ===============LICENSE_START=======================================================
.. Acumos
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

acumos-proto-viewer
===================

Dependencies
============

If you are running in Docker, there are no external dependencies, it is,
for better or worse[1], totally self contained.

If you are running locally, you will need to have redis running on the
standard port, reachable from ``localhost``.

[1] This Docker container runs Nginx, Redis, and Bokeh..

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

This application makes the directory ``/tmp/protofiles`` and uses that
for the proto files. Inside Docker this all gets cleaned up. On your
machine if you run this, be sure to clean that after. Note many OSs
automatically clean up ``/tmp`` on reboot.

Build
=====

::

    docker build -t YOURREG:18443/acumos_proto_viewer:1.0.0 .
    docker push YOURREG:18443/acumos_proto_viewer:1.0.0

Run
===

::

    docker run -dit -p 80:80 YOURREG:18443/acumos_proto_viewer:1.0.0

Optional additional env variables
---------------------------------

You can also pass in the following to alter the run behavioor:

1. UPDATE_CALLBACK_FREQUENCY // sets the frequency, in ms (1000=every
   second) of the callbacks that update the graphs on the screen, e.g.,

Fake data
=========

To launch a script that generates fake data and sends it:

::

    fake_data.py [host:port]

``[host:port]`` is an optional cmd line argument giving the target proto
to send data to; it defaults to ``localhost:5006`` for local
development.

Extra Fields
============

Every protobuf message that enters the ``/senddata`` endpoint is
injected, by this server, with additional keys:

1. ``apv_recieved_at`` : the epoch timestamp that the model was recieved
   at. Used for plotting a single variable against time
2. ``apv_model_as_string`` : the string representation of the entire
   model, used for plotting the raw text if the user chooses
3. ``apv_sequence_number`` : the sequence number of this “type” of raw
   data, where type = (model_id, message_name)
