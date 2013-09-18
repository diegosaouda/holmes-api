#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import lxml.html

from holmes.models import Review


class InvalidReviewError(RuntimeError):
    pass


class Reviewer(object):
    def __init__(self, page, validators=[]):
        self.page = page
        self.status_code = None
        self.content = None
        self.validators = validators

    def review(self):
        new_review = Review(page=self.page)

        self.load_content()
        self.run_validators(review_instance=new_review)

        return new_review

    def load_content(self):
        response = self.get_response(self.page.url)

        if response.status_code > 399:
            raise InvalidReviewError("Could not load %s!" % self.page.url)

        self.status_code = response.status_code
        self.content = response.text
        self.html = lxml.html.fromstring(self.content)

    def get_response(self, url):
        return requests.get(url)

    def run_validators(self, review_instance):
        for validator in self.validators:
            validator.validate(self, review_instance)
