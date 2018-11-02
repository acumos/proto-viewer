from setuptools import setup, find_packages

setup(
    name='acumos_proto_viewer',
    version='1.6.0',  # REPEATED IN pom.xml MUST MATCH
    packages=find_packages(),
    author="Tommy Carpenter",
    author_email="tommy@research.att.com",
    description="Probe for Acumos and ONAP to display protobuf message content",
    license="Apache 2.0",
    keywords="",
    url="https://gerrit.acumos.org/r/#/admin/projects/proto-viewer",
    zip_safe=False,
    install_requires=["requests >2.0.0, <3.0.0",
                      "jsonschema >2.0.0, <3.0.0",
                      "tornado >4.0.0, <5.0.0",
                      "bokeh >1.0.0, <3.0.0",
                      "redis >2.0.0, <3.0.0"],
    scripts=[
        "bin/fake_data.py",
        "bin/run.py"
    ],
    include_package_data=True
)
