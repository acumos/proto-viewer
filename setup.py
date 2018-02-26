from setuptools import setup, find_packages

setup(
    name='acumos_proto_viewer',
    version='1.0.0',
    packages=find_packages(),
    author="Tommy Carpenter",
    author_email="tommy@research.att.com",
    description="Probe for acumos to display Ms's data",
    license="",
    keywords="",
    url="https://gerrit.acumos.org/r/#/admin/projects/proto-viewer",
    zip_safe=False,
    install_requires=["requests"],
    scripts=[
        "bin/fake_data.py",
        "bin/run.py"
    ],
    include_package_data=True
)
