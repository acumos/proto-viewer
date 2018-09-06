from setuptools import setup, find_packages

setup(
    name='acumos_proto_viewer',
    version='1.5.5',
    packages=find_packages(),
    author="Tommy Carpenter",
    author_email="tommy@research.att.com",
    description="Probe for Acumos and ONAP to display protobuf message content",
    license="Apache 2.0",
    keywords="",
    url="https://gerrit.acumos.org/r/#/admin/projects/proto-viewer",
    zip_safe=False,
    install_requires=["requests", "jsonschema"],
    scripts=[
        "bin/fake_data.py",
        "bin/run.py"
    ],
    include_package_data=True
)
