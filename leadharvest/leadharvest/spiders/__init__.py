"""
Spiders package for LeadHarvest.
"""

from leadharvest.spiders.base import BaseLeadSpider
from leadharvest.spiders.vasep import VasepSpider
from leadharvest.spiders.vietfood import VietfoodSpider

__all__ = ["BaseLeadSpider", "VasepSpider", "VietfoodSpider"]
