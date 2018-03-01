# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [1.1.0]
* Allow the POST to contain a partial URL, and implement the ENV variable the model connector will deploy the probe with; contatenating the two forms the full probe URL.
* Start the breakout of functionality from bin/run to other modules to enable more unit testing
* Fix more (but not all) pylint violations

## [1.0.0]
* Move from modelid to protourl, and rename headers per what model connector wants
* Probe will now download the proto file from the URL
* Fix some PEP8 violations after installing FLAKE8

## [0.7.0]
* By request from Kazi, when posting into /data, return the request body back to the caller.

## [0.6.0]
* Switch to Redis so we can start TTLing datasets
* Add tests

## [0.5.0]
* Move to NGINX reverse proxy to get rid of hostname nonsense
* Add target host as a cmd line arg in `fake_data`

## [0.4.0]
* Package my own image resolver to drastically shrink page size; data URLs are huge

## [0.3.0]
* Code cleanups; move get_raw_index into a get/setter abstraction instead
* Support JPEG, make user select MIME type instead of assuming PNG
* Rename POST /senddata to POST /data to be "rest-ier"

## [0.2.0]
* Add UPDATE_CALLBACK_FREQUENCY as an env variable
* Add `apv_model_as_string` to each record
* Add `apv_sequence_number` to each record
* Add a `raw` type; still needs astetic work

## [0.1.0]
* Dockerize
* Switch from gunicorn to Tornado

## [0.0.5]
* Inject timestamp into all incoming records
* Switch graph selection and field selection
* Support image type (most of this PRs work)
* Bugfixes, cleanups.

## [0.0.4]
* Switch to a third party lib for parsing the proto file
* Move away from the proto file name being significant, to a notion of "model id" instead
* Support multiple connections

## [0.0.3]
* This changelog started
* Add input controls for selection proto file etc
* Add util functions for listing and loading compiled protos
* Added Paul's code for parsing proto file
* Added tox file
