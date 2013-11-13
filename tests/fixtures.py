#!/usr/bin/python
# -*- coding: utf-8 -*-

import factory
import factory.alchemy
from tornado.concurrent import return_future

from holmes.models import Domain, Page, Review, Worker, Violation, Fact
from uuid import uuid4


class MotorEngineFactory(factory.base.Factory):
    """Factory for motorengine objects."""
    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        return target_class(*args, **kwargs)

    @classmethod
    @return_future
    def _create(cls, target_class, *args, **kwargs):
        callback = kwargs.get('callback', None)
        del kwargs['callback']
        instance = target_class(*args, **kwargs)
        instance.save(callback=callback)


class DomainFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Domain

    name = factory.Sequence(lambda n: 'domain-{0}'.format(n))
    url = factory.Sequence(lambda n: 'http://my-site-{0}.com/'.format(n))


class PageFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Page

    #title = factory.Sequence(lambda n: 'page-{0}'.format(n))
    url = factory.Sequence(lambda n: 'http://my-site.com/{0}/'.format(n))

    created_date = None
    last_review_started_date = None
    last_review_date = None

    domain = factory.SubFactory(DomainFactory)
    last_review = None


class ReviewFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Review

    facts = factory.LazyAttribute(lambda a: [])
    violations = factory.LazyAttribute(lambda a: [])

    is_complete = False
    is_active = False
    created_date = None
    completed_date = None

    domain = factory.SubFactory(DomainFactory)
    page = factory.SubFactory(PageFactory)

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        if 'page' in kwargs:
            kwargs['domain'] = kwargs['page'].domain

        if 'number_of_violations' in kwargs:
            number_of_violations = kwargs['number_of_violations']
            del kwargs['number_of_violations']

            violations = []
            for i in range(number_of_violations):
                violations.append(Violation(
                    key="violation.%d" % i,
                    title="title %d" % i,
                    description="description %d" % i,
                    points=i
                ))

            kwargs['violations'] = violations

        return kwargs


class FactFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Fact

    title = factory.Sequence(lambda n: 'fact-{0}'.format(n))
    key = factory.Sequence(lambda n: 'fact-key-{0}'.format(n))
    unit = "value"
    value = None
    review = factory.SubFactory(ReviewFactory)


class ViolationFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Violation

    title = factory.Sequence(lambda n: 'violation-{0}'.format(n))
    key = factory.Sequence(lambda n: 'violation-key-{0}'.format(n))
    description = factory.Sequence(lambda n: 'violation-description-{0}'.format(n))
    points = 0
    review = factory.SubFactory(ReviewFactory)


class WorkerFactory(factory.alchemy.SQLAlchemyModelFactory):
    FACTORY_FOR = Worker

    uuid = factory.LazyAttribute(lambda a: uuid4())
    last_ping = None
    current_review = None
