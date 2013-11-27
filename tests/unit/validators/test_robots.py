#!/usr/bin/python
# -*- coding: utf-8 -*-

from mock import Mock
from preggy import expect

from holmes.config import Config
from holmes.reviewer import Reviewer
from holmes.validators.robots import RobotsValidator
from tests.unit.base import ValidatorTestCase
from tests.fixtures import PageFactory


class TestRobotsValidator(ValidatorTestCase):

    def test_validate_if_page_is_not_root_of_domain(self):
        page = PageFactory.create(url='http://globo.com/1')

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            config=Config(),
            validators=[]
        )

        validator = RobotsValidator(reviewer)
        validator.review.data['robots.response'] = Mock(status_code=404, text=None)
        validator.add_violation = Mock()

        validator.validate()

        expect(validator.add_violation.call_count).to_equal(0)

    def test_add_violation_when_404(self):
        page = PageFactory.create(url='http://globo.com/')

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            config=Config(),
            validators=[]
        )

        validator = RobotsValidator(reviewer)
        validator.review.data['robots.response'] = Mock(status_code=404, text=None)
        validator.add_violation = Mock()

        validator.validate()

        validator.add_violation.assert_called_once_with(
            key='robots.not_found',
            title='Robots not found',
            description='',
            points=100)

    def test_add_violation_when_empty(self):
        page = PageFactory.create(url='http://globo.com/')

        reviewer = Reviewer(
            api_url='http://localhost:2368',
            page_uuid=page.uuid,
            page_url=page.url,
            config=Config(),
            validators=[]
        )

        validator = RobotsValidator(reviewer)
        validator.review.data['robots.response'] = Mock(status_code=200, text='')
        validator.add_violation = Mock()

        validator.validate()

        validator.add_violation.assert_called_once_with(
            key='robots.empty',
            title='Empty robots file',
            description='',
            points=100)
