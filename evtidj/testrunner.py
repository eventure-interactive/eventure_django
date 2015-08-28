from django.conf import settings
from django.test.runner import DiscoverRunner


class MyTestSuiteRunner(DiscoverRunner):

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.IN_TEST_MODE = True
        settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True,
        settings.CELERY_ALWAYS_EAGER = True,
        settings.BROKER_URL = "memory://"
