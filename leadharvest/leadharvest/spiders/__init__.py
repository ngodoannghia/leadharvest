"""
Spiders package for LeadHarvest.
"""

from leadharvest.spiders.base import BaseLeadSpider
from leadharvest.spiders.vasep import VasepSpider

__all__ = ["BaseLeadSpider", "VasepSpider"]
