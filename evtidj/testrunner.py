from django.conf import settings
from django.test.runner import DiscoverRunner


class MyTestSuiteRunner(DiscoverRunner):

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.IN_TEST_MODE = True
