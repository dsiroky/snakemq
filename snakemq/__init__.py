# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
"""

import logging

############################################################################
############################################################################

def init():
    """
    Initialize logging
    """
    logger = logging.getLogger("snakemq")
    logger.setLevel(logging.CRITICAL)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
                    "%(asctime)s %(name)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
