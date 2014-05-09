#!/usr/bin/python
# -*- coding: utf-8 -*-

from gzip import GzipFile
from cStringIO import StringIO

import msgpack
from preggy import expect
from tornado.testing import gen_test
from tornado.gen import Task

from holmes.cache import Cache
from holmes.models import Domain, Limiter, Page
from tests.unit.base import ApiTestCase
from tests.fixtures import (
    DomainFactory, PageFactory, ReviewFactory, LimiterFactory
)


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
    def test_increment_active_review_count(self):
        key = 'g.com-active-review-count'
        self.cache.redis.delete(key)

        gcom = DomainFactory.create(url='http://g.com', name='g.com')
        page = PageFactory.create(domain=gcom)
        ReviewFactory.create(
            is_active=True,
            is_complete=True,
            domain=gcom,
            page=page,
            number_of_violations=1
        )

        page = PageFactory.create(domain=gcom)
        ReviewFactory.create(
            is_active=False,
            is_complete=True,
            domain=gcom,
            page=page,
            number_of_violations=3
        )

        page_count = yield self.cache.get_active_review_count('g.com')
        expect(page_count).to_equal(1)

        yield self.cache.increment_active_review_count('g.com')
        page_count = yield self.cache.get_active_review_count('g.com')
        expect(page_count).to_equal(2)

    @gen_test
    def test_can_get_active_review_count_for_domain(self):
        self.db.query(Domain).delete()

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

    @gen_test
    def test_release_lock_page(self):
        yield self.cache.lock_page('http://www.globo.com')

        result = yield self.cache.has_lock('http://www.globo.com')
        expect(result).to_be_true()

        yield self.cache.release_lock_page('http://www.globo.com')

        result = yield self.cache.has_lock('http://www.globo.com')
        expect(result).to_be_false()

    @gen_test
    def test_can_remove_domain_limiters_key(self):
        self.cache.redis.delete('domain-limiters')

        domains = yield Task(self.cache.redis.get, 'domain-limiters')
        expect(domains).to_be_null()

        yield Task(self.cache.redis.setex, 'domain-limiters', 10, 10)

        domains = yield Task(self.cache.redis.get, 'domain-limiters')
        expect(domains).to_equal('10')

        yield self.cache.remove_domain_limiters_key()

        domains = yield Task(self.cache.redis.get, 'domain-limiters')
        expect(domains).to_be_null()

    @gen_test
    def test_can_get_limit_usage(self):
        url = 'http://globo.com'
        key = 'limit-for-%s' % url
        self.cache.redis.delete(key)

        yield Task(self.cache.redis.zadd, key, {'a': 1, 'b': 2, 'c': 3})

        limit = yield Task(self.cache.redis.zcard, key)
        expect(limit).to_equal(3)

        limit = yield self.cache.get_limit_usage(url)
        expect(limit).to_equal(3)

    @gen_test
    def test_can_remove_limit_usage_by_domain(self):
        domain_url = 'http://globo.com'

        key1 = 'limit-for-%s' % domain_url
        self.cache.redis.delete(key1)

        key2 = 'limit-for-%s/sa/' % domain_url
        self.cache.redis.delete(key2)

        yield Task(self.cache.redis.zadd, key1, {'a': 1})
        yield Task(self.cache.redis.zadd, key2, {'b': 1})

        keys = yield Task(self.cache.redis.keys, 'limit-for-%s*' % domain_url)
        expect(keys).to_length(2)

        yield Task(self.cache.delete_limit_usage_by_domain, domain_url)
        keys = yield Task(self.cache.redis.keys, 'limit-for-%s*' % domain_url)
        expect(keys).to_length(0)

    @gen_test
    def test_increment_page_score(self):
        self.cache.redis.delete('pages-score')

        total = yield Task(self.cache.redis.zcard, 'page-scores')
        expect(int(total)).to_equal(0)

        yield self.cache.increment_page_score('page-1')

        score = yield Task(self.cache.redis.zscore, 'page-scores', 'page-1')
        expect(int(score)).to_equal(1)

        yield self.cache.increment_page_score('page-1')

        score = yield Task(self.cache.redis.zscore, 'page-scores', 'page-1')
        expect(int(score)).to_equal(2)


class SyncCacheTestCase(ApiTestCase):
    def setUp(self):
        super(SyncCacheTestCase, self).setUp()
        self.db.query(Domain).delete()
        self.db.query(Page).delete()

    @property
    def sync_cache(self):
        return self.connect_to_sync_redis()

    @property
    def config(self):
        return self.server.application.config

    def test_cache_has_connection_to_redis(self):
        expect(self.sync_cache.redis).not_to_be_null()

    def test_cache_has_connection_to_db(self):
        expect(self.sync_cache.db).not_to_be_null()

    def test_can_get_domain_limiters(self):
        self.db.query(Limiter).delete()
        self.sync_cache.redis.delete('domain-limiters')

        domains = self.sync_cache.get_domain_limiters()
        expect(domains).to_be_null()

        limiter = LimiterFactory.create(url='http://test.com/')
        LimiterFactory.create()
        LimiterFactory.create()

        domains = self.sync_cache.get_domain_limiters()

        expect(domains).to_length(3)
        expect(domains).to_include({limiter.url: limiter.value})

        # should get from cache
        self.sync_cache.db = None

        domains = self.sync_cache.get_domain_limiters()
        expect(domains).to_length(3)

    def test_can_set_domain_limiters(self):
        self.db.query(Limiter).delete()
        self.sync_cache.redis.delete('domain-limiters')

        domains = self.sync_cache.get_domain_limiters()
        expect(domains).to_be_null()

        limiters = [{u'http://test.com/': 10}]

        self.sync_cache.set_domain_limiters(limiters, 120)
        domains = self.sync_cache.get_domain_limiters()

        expect(domains).to_length(1)
        expect(domains).to_include(limiters[0])

    def test_has_key(self):
        self.sync_cache.redis.delete('my-key')
        has_my_key = self.sync_cache.has_key('my-key')
        expect(has_my_key).to_be_false()

        self.sync_cache.redis.setex('my-key', 10, '')
        has_my_key = self.sync_cache.has_key('my-key')
        expect(has_my_key).to_be_true()

    def test_get_domain_name(self):
        testcom = self.sync_cache.get_domain_name('test.com')
        expect(testcom).to_equal('test.com')

        gcom = DomainFactory.create(url='http://g.com', name='g.com')
        domain_name = self.sync_cache.get_domain_name(gcom)
        expect(domain_name).to_equal('g.com')

        empty_domain_name = self.sync_cache.get_domain_name('')
        expect(empty_domain_name).to_equal('page')

    def test_increment_active_review_count(self):
        key = 'g.com-active-review-count'
        self.sync_cache.redis.delete(key)

        gcom = DomainFactory.create(url='http://g.com', name='g.com')
        page = PageFactory.create(domain=gcom)
        ReviewFactory.create(
            is_active=True,
            is_complete=True,
            domain=gcom,
            page=page,
            number_of_violations=1
        )

        page = PageFactory.create(domain=gcom)
        ReviewFactory.create(
            is_active=False,
            is_complete=True,
            domain=gcom,
            page=page,
            number_of_violations=3
        )

        self.sync_cache.increment_active_review_count(gcom.name)
        active_review_count = self.sync_cache.redis.get(key)
        expect(active_review_count).to_equal('1')

        self.sync_cache.increment_active_review_count(gcom.name)
        active_review_count = self.sync_cache.redis.get(key)
        expect(active_review_count).to_equal('2')

    def test_increment_count(self):
        key = 'g.com-my-key'
        self.sync_cache.redis.delete(key)

        gcom = DomainFactory.create(url="http://g.com", name="g.com")
        PageFactory.create(domain=gcom)

        self.sync_cache.increment_count(
            'my-key',
            gcom.name,
            lambda domain: domain.get_page_count(self.db)
        )
        page_count = self.sync_cache.redis.get(key)
        expect(page_count).to_equal('1')

        self.sync_cache.increment_count(
            'my-key',
            gcom.name,
            lambda domain: domain.get_page_count(self.db)
        )
        page_count = self.sync_cache.redis.get(key)
        expect(page_count).to_equal('2')

    def test_get_active_review_count(self):
        self.sync_cache.redis.delete('g.com-active-review-count')

        gcom = DomainFactory.create(url="http://g.com", name="g.com")
        DomainFactory.create(url="http://g1.globo.com", name="g1.globo.com")

        page = PageFactory.create(domain=gcom)
        page2 = PageFactory.create(domain=gcom)

        ReviewFactory.create(
            is_active=True,
            is_complete=True,
            domain=gcom,
            page=page,
            number_of_violations=10
        )
        ReviewFactory.create(
            is_active=True,
            is_complete=True,
            domain=gcom,
            page=page2,
            number_of_violations=10
        )
        ReviewFactory.create(
            is_active=False,
            is_complete=True,
            domain=gcom,
            page=page2,
            number_of_violations=10
        )

        count = self.sync_cache.get_active_review_count(gcom.name)
        expect(count).to_equal(2)

        # should get from cache
        self.sync_cache.db = None

        count = self.sync_cache.get_active_review_count(gcom.name)
        expect(count).to_equal(2)

    def test_get_count(self):
        key = 'g.com-my-key'
        self.sync_cache.redis.delete(key)

        gcom = DomainFactory.create(url="http://g.com", name="g.com")
        PageFactory.create(domain=gcom)

        count = self.sync_cache.get_count(
            key,
            gcom.name,
            int(self.config.PAGE_COUNT_EXPIRATION_IN_SECONDS),
            lambda domain: domain.get_page_count(self.db)
        )
        expect(count).to_equal(1)

        # should get from cache
        self.sync_cache.db = None

        count = self.sync_cache.get_count(
            key,
            gcom.name,
            int(self.config.PAGE_COUNT_EXPIRATION_IN_SECONDS),
            lambda domain: domain.get_page_count(self.db)
        )
        expect(count).to_equal(1)

    def test_get_request_with_url_not_cached(self):
        url = 'http://g.com/test.html'
        key = 'urls-%s' % url

        self.sync_cache.redis.delete(key)

        url, response = self.sync_cache.get_request(url)

        expect(url).to_equal('http://g.com/test.html')
        expect(response).to_be_null()

    def test_get_request_with_url_cached(self):
        url = 'http://g.com/test.html'
        key = 'urls-%s' % url

        self.sync_cache.redis.delete(key)

        out = StringIO()
        with GzipFile(fileobj=out, mode="w") as f:
            f.write('')
        text = out.getvalue()

        value = msgpack.packb({
            'url': url,
            'body': text,
            'status_code': 200,
            'headers': None,
            'cookies': None,
            'effective_url': 'http://g.com/test.html',
            'error': None,
            'request_time': str(100)
        })


        self.sync_cache.redis.setex(
            key,
            10,
            value
        )

        url, response = self.sync_cache.get_request(url)

        expect(url).to_equal('http://g.com/test.html')
        expect(response.status_code).to_equal(200)
        expect(response.effective_url).to_equal(url)
        expect(response.request_time).to_equal(100)

    def test_set_request(self):
        test_url = 'http://g.com/test.html'
        key = 'urls-%s' % test_url

        self.sync_cache.redis.delete(key)

        url, response = self.sync_cache.get_request(test_url)
        expect(url).to_equal('http://g.com/test.html')
        expect(response).to_be_null()

        self.sync_cache.set_request(
            url=url,
            status_code=200,
            headers={'X-HEADER': 'test'},
            cookies=None,
            text='',
            effective_url='http://g.com/test.html',
            error=None,
            request_time=100,
            expiration=5
        )

        url, response = self.sync_cache.get_request(test_url)

        expect(url).to_equal('http://g.com/test.html')
        expect(response.status_code).to_equal(200)
        expect(response.headers.get('X-HEADER')).to_equal('test')
        expect(response.cookies).to_be_null()
        expect(response.effective_url).to_equal(url)
        expect(response.error).to_be_null()
        expect(response.request_time).to_equal(100)

    def test_set_request_with_status_code_greater_than_399(self):
        test_url = 'http://g.com/test.html'
        key = 'urls-%s' % test_url

        self.sync_cache.redis.delete(key)

        self.sync_cache.set_request(
            url=test_url,
            status_code=500,
            headers=None,
            cookies=None,
            text=None,
            effective_url=None,
            error=None,
            request_time=1,
            expiration=5
        )

        url, response = self.sync_cache.get_request(test_url)
        expect(url).to_equal('http://g.com/test.html')
        expect(response).to_be_null()

    def test_set_request_with_status_code_less_than_100(self):
        test_url = 'http://g.com/test.html'
        key = 'urls-%s' % test_url

        self.sync_cache.redis.delete(key)

        self.sync_cache.set_request(
            url=test_url,
            status_code=99,
            headers=None,
            cookies=None,
            text=None,
            effective_url=None,
            error=None,
            request_time=1,
            expiration=5
        )

        url, response = self.sync_cache.get_request(test_url)
        expect(url).to_equal('http://g.com/test.html')
        expect(response).to_be_null()

    def test_lock_next_job(self):
        test_url = 'http://g.com/test.html'
        key = '%s-next-job-lock' % test_url

        self.sync_cache.redis.delete(key)

        lock = self.sync_cache.lock_next_job(test_url, 5)

        expect(lock.acquire()).to_be_true()

    def test_has_next_job_lock(self):
        test_url = 'http://g.com/test.html'
        key = '%s-next-job-lock' % test_url

        self.sync_cache.redis.delete(key)

        lock = self.sync_cache.lock_next_job(test_url, 20)
        expect(lock).not_to_be_null()

        has_next_job_lock = self.sync_cache.has_next_job_lock(test_url, 20)
        expect(has_next_job_lock).not_to_be_null()

        has_next_job_lock = self.sync_cache.has_next_job_lock(test_url, 20)
        expect(has_next_job_lock).to_be_null()

    def test_release_next_job(self):
        test_url = 'http://g.com/test.html'
        key = '%s-next-job-lock' % test_url

        self.sync_cache.redis.delete(key)

        has_next_job_lock = self.sync_cache.has_next_job_lock(test_url, 5)
        expect(has_next_job_lock).not_to_be_null()

        self.sync_cache.release_next_job(has_next_job_lock)

        lock = self.sync_cache.has_next_job_lock(test_url, 5)
        expect(lock).not_to_be_null()

    def test_increment_page_score(self):
        self.sync_cache.redis.delete('page-scores')

        total = self.sync_cache.redis.zcard('page-scores')
        expect(total).to_equal(0)

        self.sync_cache.increment_page_score('page-1')

        score = self.sync_cache.redis.zscore('page-scores', 'page-1')
        expect(score).to_equal(1)

        self.sync_cache.increment_page_score('page-1')

        score = self.sync_cache.redis.zscore('page-scores', 'page-1')
        expect(score).to_equal(2)

    def test_seized_pages_score(self):
        self.sync_cache.redis.delete('page-scores')

        for i in range(3):
            self.sync_cache.increment_page_score('page-%d' % i)

        total = self.sync_cache.redis.zcard('page-scores')
        expect(total).to_equal(3)

        values = self.sync_cache.seized_pages_score()
        expect(values).to_length(3)

        total = self.sync_cache.redis.zcard('page-scores')
        expect(total).to_equal(0)

    def test_lock_update_pages_score(self):
        self.sync_cache.redis.delete('update-pages-score-lock')

        lock = self.sync_cache.lock_update_pages_score(5)

        expect(lock.acquire()).to_be_true()

    def test_has_update_pages_lock(self):
        self.sync_cache.redis.delete('update-pages-score-lock')

        lock = self.sync_cache.lock_update_pages_score(20)
        expect(lock).not_to_be_null()

        has_update_pages_lock = self.sync_cache.has_update_pages_lock(20)
        expect(has_update_pages_lock).not_to_be_null()

        has_update_pages_lock = self.sync_cache.has_update_pages_lock(20)
        expect(has_update_pages_lock).to_be_null()

    def test_release_update_pages_lock(self):
        self.sync_cache.redis.delete('update-pages-score-lock')

        has_update_pages_lock = self.sync_cache.has_update_pages_lock(5)
        expect(has_update_pages_lock).not_to_be_null()

        self.sync_cache.release_update_pages_lock(has_update_pages_lock)

        lock = self.sync_cache.has_update_pages_lock(5)
        expect(lock).not_to_be_null()
