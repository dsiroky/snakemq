from setuptools import setup, find_packages

from snakemq import version

setup(name="snakeMQ",
      version=version.VERSION,
      description="message queuing for Python",
      long_description = open("README.md").read(),
      long_description_content_type='text/markdown',
      keywords=("message, messaging, queue, persistent, network, communication, "
                "reconnect, RPC"),
      author="David Siroky",
      author_email="siroky@dasir.cz",
      url="http://www.snakemq.net",
      license="MIT License",
      classifiers=[
          "Operating System :: OS Independent",
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Topic :: System :: Networking",
          "Topic :: System :: Distributed Computing",
          "Topic :: Communications",
          "Topic :: Internet",
          "Topic :: Software Development :: Libraries",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.0",
          "Programming Language :: Python :: 3.1",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
        ],
      packages=find_packages()
    )
