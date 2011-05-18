from setuptools import setup, find_packages

from snakemq import version

setup(name="snakeMQ",
      version=version.VERSION,
      description="message queuing for Python",
      long_description = open("README.txt").read(),
      keywords=("message, messaging, queue, persistent, network, communication, "
                "reconnect, RPC"),
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
      packages=find_packages(),
      tests_require=["nose"],
      test_suite="nose.collector"
    )
