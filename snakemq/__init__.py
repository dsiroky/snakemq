# -*- coding: utf-8 -*-
"""
@author: David Siroky (siroky@dasir.cz)
@license: MIT License (see LICENSE.txt or
          U{http://www.opensource.org/licenses/mit-license.php})
"""

import logging

############################################################################
############################################################################

# TODO create generic init() which must be called always
def init_logging():
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
