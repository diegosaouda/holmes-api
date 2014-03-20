#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib
from os.path import abspath, dirname, join

from cow.testing import CowTestCase
from tornado.httpclient import AsyncHTTPClient
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from holmes.config import Config
from holmes.server import HolmesApiServer
from tests.fixtures import (
    DomainFactory, PageFactory, ReviewFactory, FactFactory,
    ViolationFactory, WorkerFactory, KeyFactory, KeysCategoryFactory,
    RequestFactory, UserFactory, LimiterFactory
)


autoflush = True
engine = create_engine(
    "mysql+mysqldb://root@localhost:3306/test_holmes",
    convert_unicode=True,
    pool_size=1,
    max_overflow=0,
    echo=False
)
maker = sessionmaker(bind=engine, autoflush=autoflush)
db = scoped_session(maker)


class ApiTestCase(CowTestCase):
    ZERO_UUID = '00000000-0000-0000-0000-000000000000'

    def drop_collection(self, document):
        document.objects.delete(callback=self.stop)
        self.wait()

    def setUp(self):
        super(ApiTestCase, self).setUp()

        DomainFactory.FACTORY_SESSION = self.db
        PageFactory.FACTORY_SESSION = self.db
        ReviewFactory.FACTORY_SESSION = self.db
        FactFactory.FACTORY_SESSION = self.db
        ViolationFactory.FACTORY_SESSION = self.db
        WorkerFactory.FACTORY_SESSION = self.db
        KeyFactory.FACTORY_SESSION = self.db
        KeysCategoryFactory.FACTORY_SESSION = self.db
        RequestFactory.FACTORY_SESSION = self.db
        UserFactory.FACTORY_SESSION = self.db
        LimiterFactory.FACTORY_SESSION = self.db

        self.clean_cache('www.globo.com')
        self.clean_cache('globo.com')
        self.clean_cache('g1.globo.com')

    def tearDown(self):
        self.db.rollback()
        super(ApiTestCase, self).tearDown()

    def get_config(self):
        return dict(
            SQLALCHEMY_CONNECTION_STRING="mysql+mysqldb://root@localhost:3306/test_holmes",
            SQLALCHEMY_POOL_SIZE=1,
            SQLALCHEMY_POOL_MAX_OVERFLOW=0,
            SQLALCHEMY_AUTO_FLUSH=True,
            COMMIT_ON_REQUEST_END=False,
            REDISHOST='localhost',
            REDISPORT=57575,
            MATERIAL_GIRL_REDISHOST='localhost',
            MATERIAL_GIRL_REDISPORT=57575,
        )

    def get_server(self):
        cfg = Config(**self.get_config())
        debug = os.environ.get('DEBUG_TESTS', 'False').lower() == 'true'

        self.server = HolmesApiServer(config=cfg, debug=debug, db=db)
        return self.server

    def get_app(self):
        app = super(ApiTestCase, self).get_app()
        app.http_client = AsyncHTTPClient(self.io_loop)
        self.db = app.db

        return app

    def clean_cache(self, domain_name):
        do_nothing = lambda *args, **kw: None

        url_hash = hashlib.sha512('http://%s' % domain_name).hexdigest()

        self.server.application.redis.delete('%s-lock' % url_hash, callback=do_nothing)
        self.server.application.redis.delete('%s-page-count' % domain_name, callback=do_nothing)
        self.server.application.redis.delete('%s-violation-count' % domain_name, callback=do_nothing)
        self.server.application.redis.delete('%s-active-review-count' % domain_name, callback=do_nothing)
        self.server.application.redis.delete('%s-good-request-count' % domain_name, callback=do_nothing)
        self.server.application.redis.delete('%s-bad-request-count' % domain_name, callback=do_nothing)
        self.server.application.redis.delete('%s-response-time-avg' % domain_name, callback=do_nothing)

    def connect_to_sync_redis(self):
        import redis
        from holmes.cache import SyncCache

        host = self.server.application.config.get('REDISHOST')
        port = self.server.application.config.get('REDISPORT')

        redis = redis.StrictRedis(host=host, port=port, db=0)

        return SyncCache(self.db, redis, self.server.application.config)

FILES_ROOT_PATH = abspath(join(dirname(__file__), 'files'))


class ValidatorTestCase(ApiTestCase):

    def get_file(self, name):
        with open(join(FILES_ROOT_PATH.rstrip('/'), name.lstrip('/')), 'r') as local_file:
            return local_file.read()


class FacterTestCase(ValidatorTestCase):
    pass
