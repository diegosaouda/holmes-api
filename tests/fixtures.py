#!/usr/bin/python
# -*- coding: utf-8 -*-

import factory

from holmes.models import Domain, Page
from tests.base import MotorEngineFactory


class DomainFactory(MotorEngineFactory):
    FACTORY_FOR = Domain

    name = factory.Sequence(lambda n: 'domain-{0}'.format(n))
    url = factory.Sequence(lambda n: 'http://my-site-{0}.com/'.format(n))


class PageFactory(MotorEngineFactory):
    FACTORY_FOR = Page

    title = factory.Sequence(lambda n: 'page-{0}'.format(n))
    url = factory.Sequence(lambda n: 'http://my-site.com/{0}/'.format(n))

    added_date = None
    updated_date = None

    domain = factory.SubFactory(DomainFactory)
    #last_processing = factory.SubFactory(LastProcessingFactory)
