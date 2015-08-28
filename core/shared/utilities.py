from django.conf import settings
from django.core.urlresolvers import reverse


def get_absolute_url(viewname, urlconf=None, args=None, kwargs=None, current_app=None):
    """Get the absolute url for a view.

    Builds based off of SITE_URL in settings and the view information.
    """
    return settings.SITE_URL.rstrip("/") + reverse(viewname,
                                                   urlconf=urlconf,
                                                   args=args,
                                                   kwargs=kwargs,
                                                   current_app=current_app)
