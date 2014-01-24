#!/usr/bin/python
# -*- coding: utf-8 -*-

from os.path import abspath, dirname, join

from preggy import expect
from mock import patch, Mock, call
from octopus import TornadoOctopus

from holmes import __version__
from holmes.worker import HolmesWorker
from holmes.config import Config
from tests.unit.base import ApiTestCase


class MockResponse(object):
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self.text = text


class WorkerTestCase(ApiTestCase):
    root_path = abspath(join(dirname(__file__), '..', '..'))

    @patch('uuid.UUID')
    def test_initialize(self, uuid):
        uuid.return_value = Mock(hex='my-uuid4')

        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf'), '--concurrency=10'])
        worker.initialize()

        expect(worker.uuid).to_equal('my-uuid4')
        expect(worker.working).to_be_true()

        expect(worker.facters).to_length(1)
        expect(worker.validators).to_length(1)

        expect(worker.otto).to_be_instance_of(TornadoOctopus)

    def test_config_parser(self):
        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf')])

        parser_mock = Mock()

        worker.config_parser(parser_mock)

        expect(parser_mock.add_argument.call_args_list).to_include(
            call(
                '--concurrency',
                '-t',
                type=int,
                default=10,
                help='Number of threads (or async http requests) to use for '
                     'Octopus (doing GETs concurrently)'
            ))

        expect(parser_mock.add_argument.call_args_list).to_include(
            call(
                '--cache',
                default=False,
                action='store_true',
                help='Whether http requests should be cached by Octopus.'
            ))

    def test_proxies_property(self):
        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf')])

        expect(worker.proxies).to_be_like({
            'http': 'http://proxy:8080',
            'https': 'http://proxy:8080'
        })

    def test_tornado_async_get(self):
        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf')])

        otto_mock = Mock()
        worker.otto = otto_mock

        worker.async_get("url", "handler", 'GET', test="test")
        otto_mock.enqueue.assert_called_once_with(
            'url', 'handler', 'GET', test='test', proxy_host='http://proxy', proxy_port=8080
        )

    def test_description(self):
        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf')])

        expected = "holmes-worker (holmes-api v%s)" % (
            __version__
        )

        expect(worker.get_description()).to_be_like(expected)

    def test_config_class(self):
        worker = HolmesWorker(['-c', join(self.root_path, 'tests/unit/test_worker.conf')])

        expect(worker.get_config_class()).to_equal(Config)
