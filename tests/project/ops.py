"""A second admin site, mounted alongside the first.

Its only job is to prove that URL resolution follows the site it is given rather
than the default one. It registers Product and nothing else, so it also differs from
the default site in what it knows about.
"""

from django.contrib.admin.sites import AdminSite

from .shop.models import Product

ops_site = AdminSite(name="ops")
ops_site.register(Product)
