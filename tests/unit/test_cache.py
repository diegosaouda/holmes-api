#!/usr/bin/python
# -*- coding: utf-8 -*-

from preggy import expect
from tornado.testing import gen_test
from tornado.gen import Task

from holmes.cache import Cache
from tests.unit.base import ApiTestCase
from tests.fixtures import DomainFactory, PageFactory, ReviewFactory


class CacheTestCase(ApiTestCase):
    @property
    def cache(self):
        return self.server.application.cache

    def test_cache_is_in_server(self):
        expect(self.server.application.cache).to_be_instance_of(Cache)

    def test_cache_has_connection_to_redis(self):
        expect(self.server.application.cache.redis).not_to_be_null()

    def test_cache_has_connection_to_db(self):
        expect(self.server.application.cache.db).not_to_be_null()

    @gen_test
    def test_can_get_page_count_per_domain(self):
        globocom = DomainFactory.create(url="http://globo.com", name="globo.com")
        g1 = DomainFactory.create(url="http://g1.globo.com", name="g1.globo.com")

        for i in range(2):
            PageFactory.create(domain=globocom)
            PageFactory.create(domain=g1)

        PageFactory.create(domain=g1)

        page_count = yield self.cache.get_page_count('globo.com')
        expect(page_count).to_equal(2)

        page_count = yield self.cache.get_page_count('g1.globo.com')
        expect(page_count).to_equal(3)

        # should get from cache
        self.cache.db = None

        page_count = yield self.cache.get_page_count('g1.globo.com')
        expect(page_count).to_equal(3)

    @gen_test
    def test_can_increment_page_count(self):
        globocom = DomainFactory.create(url="http://globo.com", name="globo.com")

        for i in range(2):
            PageFactory.create(domain=globocom)

        page_count = yield self.cache.get_page_count('globo.com')
        expect(page_count).to_equal(2)

        page_count = yield self.cache.increment_page_count('globo.com', 10)
        expect(page_count).to_equal(12)

    @gen_test
    def test_can_get_violation_count_for_domain(self):
        globocom = DomainFactory.create(url="http://globo.com", name="globo.com")

        page = PageFactory.create(domain=globocom)
        ReviewFactory.create(is_active=True, is_complete=True, domain=globocom, page=page, number_of_violations=10)

        violation_count = yield self.cache.get_violation_count('globo.com')
        expect(violation_count).to_equal(10)

        # should get from cache
        self.cache.db = None

        violation_count = yield self.cache.get_violation_count('globo.com')
        expect(violation_count).to_equal(10)

    @gen_test
    def test_can_get_active_review_count_for_domain(self):
        globocom = DomainFactory.create(url="http://globo.com", name="globo.com")
        DomainFactory.create(url="http://g1.globo.com", name="g1.globo.com")

        page = PageFactory.create(domain=globocom)
        ReviewFactory.create(is_active=True, is_complete=True, domain=globocom, page=page, number_of_violations=10)
        page2 = PageFactory.create(domain=globocom)
        ReviewFactory.create(is_active=True, is_complete=True, domain=globocom, page=page2, number_of_violations=10)
        ReviewFactory.create(is_active=False, is_complete=True, domain=globocom, page=page2, number_of_violations=10)

        count = yield self.cache.get_active_review_count('globo.com')
        expect(count).to_equal(2)

        # should get from cache
        self.cache.db = None

        count = yield self.cache.get_active_review_count('globo.com')
        expect(count).to_equal(2)

    @gen_test
    def test_can_store_processed_page_lock(self):
        yield self.cache.lock_page('http://www.globo.com')

        result = yield Task(self.cache.redis.get, 'http://www.globo.com-lock')
        expect(int(result)).to_equal(1)

    @gen_test
    def test_can_get_url_was_added(self):
        yield self.cache.lock_page('http://www.globo.com')

        result = yield self.cache.has_lock('http://www.globo.com')
        expect(result).to_be_true()
