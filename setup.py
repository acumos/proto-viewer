import os
from setuptools import setup, find_packages
from pip.req import parse_requirements
from pip.download import PipSession

setup(
    name='acumos_proto_viewer',
    version='0.7.1',
    packages=find_packages(),
    author = "Tommy Carpenter",
    author_email = "",
    description="Probe for acumos to display Ms's data",
    license = "",
    keywords = "",
    url = "https://gerrit.acumos.org/r/#/admin/projects/proto-viewer",
    zip_safe=False,
    scripts = [
        "bin/fake_data.py",
        "bin/run.py"
    ],
    data_files=[
                   (".", ['.config', 'swagger/swagger.yaml', 'theme.yaml']),
                   ("templates", ["templates/embed.html"]),
                   ("test_proto", ["test_proto/test.proto", "test_proto/test3.proto", "test_proto/test_paul.proto"])
               ]
)
