#!/usr/bin/python
# -*- coding: utf-8 -*-

from mock import Mock, call
from preggy import expect

from holmes.config import Config
from holmes.reviewer import Reviewer
from holmes.validators.google_analytics import GoogleAnalyticsValidator
from tests.fixtures import PageFactory
from tests.unit.base import ValidatorTestCase


class TestGoogleAnalyticsValidator(ValidatorTestCase):

    def test_validate(self):
        config = Config()

        page = PageFactory.create()

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            page_score=0.0,
            config=config,
            validators=[]
        )

        validator = GoogleAnalyticsValidator(reviewer)
        validator.add_violation = Mock()
        validator.review.data = {
            'page.google_analytics': set([('UA-296593-2', 'www.globo.com')]),
        }

        validator.validate()

        expect(validator.add_violation.called).to_be_false()

    def test_page_without_google_analytics(self):
        config = Config()

        page = PageFactory.create()

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            page_score=0.0,
            config=config,
            validators=[]
        )

        validator = GoogleAnalyticsValidator(reviewer)
        validator.add_violation = Mock()
        validator.review.data = {
            'page.google_analytics': set([]),
        }

        validator.validate()

        expect(validator.add_violation.call_args_list).to_include(
            call(
                key='google_analytics.not_found',
                points=100,
                value=None
            ))

    def test_page_without_google_analytics_account(self):
        config = Config()

        page = PageFactory.create()

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            page_score=0.0,
            config=config,
            validators=[]
        )

        validator = GoogleAnalyticsValidator(reviewer)
        validator.add_violation = Mock()
        validator.review.data = {
            'page.google_analytics': set([(None, 'www.globo.com')]),
        }

        validator.validate()

        expect(validator.add_violation.call_args_list).to_include(
            call(
                key='google_analytics.account.not_found',
                points=50,
                value=None
            ))

    def test_page_without_google_analytics_domain(self):
        config = Config()

        page = PageFactory.create()

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            page_score=0.0,
            config=config,
            validators=[]
        )

        validator = GoogleAnalyticsValidator(reviewer)
        validator.add_violation = Mock()
        validator.review.data = {
            'page.google_analytics': set([('UA-296593-2', None)]),
        }

        validator.validate()

        expect(validator.add_violation.call_args_list).to_include(
            call(
                key='google_analytics.domain.not_found',
                points=50,
                value=None
            ))

    def test_can_get_violation_definitions(self):
        reviewer = Mock()
        validator = GoogleAnalyticsValidator(reviewer)

        definitions = validator.get_violation_definitions()

        expect(definitions).to_length(3)
        expect('google_analytics.not_found' in definitions).to_be_true()
        expect('google_analytics.account.not_found' in definitions).to_be_true()
        expect('google_analytics.domain.not_found' in definitions).to_be_true()

        not_found_def = definitions['google_analytics.not_found']
        account_not_found_def = definitions['google_analytics.account.not_found']
        domain_not_found_def = definitions['google_analytics.domain.not_found']

        for vd in [not_found_def, account_not_found_def, domain_not_found_def]:
            expect('title' in vd).to_be_true()
            expect('description' in vd).to_be_true()
            expect('category' in vd).to_be_true()
            expect('generic_description' in vd).to_be_true()

