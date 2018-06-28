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
    b. The `npm` tool, version 2.15.5 or later
    c. The `npm` package `protobuf-jsonschema`, version 1.1.1 or later (`npm install protobuf-jsonschema`)

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

We have used a shared Nexus registry for this; any web server is fine.  To use the fake-data injector the server must have these test files::

    probe_testxyz_100_proto
    probe_testimage_100_proto
    image_mood_classification_100_proto

7. Launch the Bokeh-enabled web server::

    ./apv36/bin/python3 bin/run.py

8. Start the data-injection script::

    ./apv36/bin/python3 fake_data.py

9. Open a web browser::

    http://localhost:5006

Never ever try to change the port. It will not work. It will evolve to endless suffering. Darkness will envelop you.  Essentially there's a bug in Bokeh.

Dependencies
============

If you are running in Docker there are no external dependencies, for better or worse[1] it is totally self contained.

If you are running locally, please follow the quickstart above.

[1] This Docker container runs Nginx, Redis, and Bokeh. The original requirements stated that the probe had to be a single Docker container.

Design
======

The proto-viewer enables viewing of binary-encoded protocol buffer messages
passed among elements of a composite solution. To display message content
the proto-viewer must parse the binary message using a protocol buffer message
definition file. Those files are obtained dynamically by the proto-viewer
from network sources.

Messages are passed to the proto-viewer by the Acumos blueprint orchestrator
component, also known as the model connector.  The model connector makes HTTP POST
calls to deliver a copy of each message to the proto-viewer along with details
about the message definition.

Each message POST-ed to the proto-viewer must contain only binary Protocol-Buffer
encoded content, and must include the following HTTP headers::

    PROTO-URL
    Message-Name

The "PROTO-URL" parameter can be either a complete URL (e.g., "http://host:port/path/to/file")
or just a suffix (e.g., "/path/to/file").  The URL is used to fetch the protocol
buffer specification file for the message.  The "Message-Name" parameter specifies the
name of the message (data structure) within that protocol buffer specification file,
which may define multiple messages.

If the PROTO-URL header parameter is just a suffix, the value of this environment
variable is consulted::

    NEXUSENDPOINTURL

This is expected to contain the prefix of a URL where the protocol buffer file can be
obtained; e.g., "http://host:port/context/path".

When the probe is sent the URL of a protocol buffer definition file, the probe
downloads the .proto file and caches it for reuse if the same URL is encountered
again. One complication here is that the protoc tool fails for input files that
contain a dot or hyphen in the filename, so the filenames are mangled by the
proto-viewer to remove all offending characters.

The probe then invokes the "protoc" compiler on the definition file to generate a
Python module, working in a temporary directory.  Finally the proto-viewer imports
the newly created Python module and uses it to parse binary messages.

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
