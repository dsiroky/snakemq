from setuptools import setup

from snakemq import version

setup(name="snakeMQ",
      version=version.VERSION,
      description="message queuing for Python",
      long_description = file("README.txt").read(),
      author="David Siroky",
      author_email="siroky@dasir.cz",
      url="http://www.snakemq.net",
      license="MIT License",
      classifiers=[
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Topic :: System :: Networking"
        ],
      packages=["snakemq"]
    )
