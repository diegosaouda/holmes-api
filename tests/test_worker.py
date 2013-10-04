#!/usr/bin/python
# -*- coding: utf-8 -*-

from os.path import abspath, dirname, join

from preggy import expect
from mock import patch, Mock
from requests.exceptions import ConnectionError
from requests import Response
from tornado.testing import gen_test
import requests

import holmes.worker
from tests.base import ApiTestCase
from tests.fixtures import DomainFactory, PageFactory, ReviewFactory


class WorkerTestCase(ApiTestCase):
    root_path = abspath(join(dirname(__file__), ".."))

    def get_config(self):
        cfg = super(WorkerTestCase, self).get_config()
        cfg['WORKER_SLEEP_TIME'] = 1
        cfg['HOLMES_API_URL'] = "http://localhost:2368"

        return cfg

    @patch('holmes.worker.HolmesWorker')
    def test_worker_main_function(self, worker_mock):
        holmes.worker.main()
        expect(worker_mock().run.called).to_be_true()

    @patch('time.sleep')
    def test_worker_sleep_time(self, worker_sleep):
        worker = holmes.worker.HolmesWorker()
        worker.run()
        worker_sleep.assert_called_once_with(1)

    def test_worker_working_flag(self):
        worker = holmes.worker.HolmesWorker()

        expect(worker.working).to_be_true()
        worker.stop_work()
        expect(worker.working).to_be_false()

    @patch.object(holmes.worker.HolmesWorker, '_do_work')
    def test_worker_run_keyboard_interrupt(self, do_work_mock):
        do_work_mock.side_effect = KeyboardInterrupt()

        worker = holmes.worker.HolmesWorker()
        worker.run()
        expect(worker.working).to_be_false()

    def test_worker_can_create_an_instance(self):
        worker = holmes.worker.HolmesWorker()
        expect(worker.working).to_be_true()
        expect(worker.config.VALIDATORS).to_equal([])

    def test_worker_can_parse_opt(self):
        worker = holmes.worker.HolmesWorker()
        expect(worker.options.conf).not_to_equal("test.conf")
        expect(worker.options.verbose).to_equal(0)

        worker._parse_opt(arguments=["-c", "test.conf", "-vv"])
        expect(worker.options.conf).to_equal("test.conf")
        expect(worker.options.verbose).to_equal(2)

    def test_worker_can_create_an_instance_with_config_file(self):
        worker = holmes.worker.HolmesWorker(['-c', join(self.root_path, './tests/config/test_one_validator.conf')])
        expect(worker.config.VALIDATORS).to_length(1)

    @patch('holmes.worker.verify_config')
    def test_worker_validating_config_load(self, verify_config_mock):
        worker = holmes.worker.HolmesWorker()
        worker._load_config(verify=True)
        expect(verify_config_mock.called).to_be_true()

    def test_worker_logging_config_from_arguments(self):
        worker = holmes.worker.HolmesWorker(["", "-v"])
        log_level = worker._config_logging()
        expect(log_level).to_equal("WARNING")

    def test_worker_logging_config_from_file(self):
        worker = holmes.worker.HolmesWorker(['-c', join(self.root_path, './tests/config/test_one_validator.conf')])
        log_level = worker._config_logging()
        expect(log_level).to_equal("INFO")

    @patch('holmes.reviewer.Reviewer')
    def test_worker_do_work(self, reviewer_mock):
        worker = holmes.worker.HolmesWorker()
        domain = yield DomainFactory.create()
        page = yield PageFactory.create(domain=domain)
        worker._do_work(page)
        expect(reviewer_mock().called).to_be_true()

    @patch.object(holmes.worker.HolmesWorker, '_ping_api')
    def test_worker_do_work_calling_ping_api(self, ping_api_mock):
        worker = holmes.worker.HolmesWorker()
        worker._do_work()
        expect(ping_api_mock.called).to_be_true()

    @patch('requests.post')
    def test_worker_ping_api(self, requests_mock):
        worker = holmes.worker.HolmesWorker()
        worker._ping_api()
        expect(requests_mock.called).to_be_true()
        requests_mock.assert_called_once_with(
            "http://localhost:2368/worker/ping",
            data={"worker_uuid": worker.uuid}
        )

    @patch('requests.post')
    def test_worker_ping_api_connection_error(self, ping_api_mock):
        ping_api_mock.side_effect = ConnectionError()

        worker = holmes.worker.HolmesWorker()
        was_successful = worker._ping_api()
        expect(worker.working).to_be_false()
        expect(was_successful).to_be_false()

    @patch('requests.get')
    def test_worker_load_next_job_error(self, load_next_job_mock):
        load_next_job_mock.side_effect = ConnectionError()

        worker = holmes.worker.HolmesWorker()
        worker._load_next_job()
        expect(worker.working).to_be_false()

    @patch('requests.get')
    def test_worker_load_next_job_must_call_api(self, load_next_job_mock):
        response = Response()
        response.status_code = 200
        response.body = ""
        load_next_job_mock.return_value = response

        worker = holmes.worker.HolmesWorker()
        worker._load_next_job()

        expect(load_next_job_mock.called).to_be_true()
        load_next_job_mock.assert_called_once_with("http://localhost:2368/next")

    @patch('requests.get')
    def test_worker_load_next_job_without_jobs(self, load_next_job_mock):
        response = Response()
        response.status_code = 200
        response.body = ""

        load_next_job_mock.return_value = response

        worker = holmes.worker.HolmesWorker()
        next_job = worker._load_next_job()

        expect(next_job).to_be_null()

    @gen_test
    def test_worker_load_next_job(self):
        domain = yield DomainFactory.create()
        page = yield PageFactory.create(domain=domain)
        review = yield ReviewFactory.create(page=page)

        response = Response()
        response.status_code = 200
        response.body = '{"page": "%s", "review": "%s", "url": "%s"}' % \
                        (str(page.uuid), str(review.uuid), page.url)

        requests.get = Mock(return_value=response)

        worker = holmes.worker.HolmesWorker()
        next_job = worker._load_next_job()

        expect(next_job).not_to_be_null()
        expect(next_job['page']).to_equal(str(page.uuid))
        expect(next_job['review']).to_equal(str(review.uuid))
        expect(next_job['url']).to_equal(str(page.url))

    @patch('requests.post')
    def test_worker_start_error(self, load_start_job_mock):
        load_start_job_mock.side_effect = ConnectionError()

        worker = holmes.worker.HolmesWorker()
        worker._start_job("000")
        expect(worker.working).to_be_true()

    @patch('requests.post')
    def test_worker_start_call_api(self, requests_mock):
        worker = holmes.worker.HolmesWorker()
        worker._start_job("000")
        expect(requests_mock.called).to_be_true()
        requests_mock.assert_called_once_with(
            "http://localhost:2368/worker/%s/start/000" % str(worker.uuid)
        )

    @patch('requests.post')
    def test_worker_complete_error(self, load_start_job_mock):
        load_start_job_mock.side_effect = ConnectionError()

        worker = holmes.worker.HolmesWorker()
        worker._complete_job("000")
        expect(worker.working).to_be_true()

    @patch('requests.post')
    def test_worker_complete_call_api(self, requests_mock):
        worker = holmes.worker.HolmesWorker()
        worker._complete_job("000")
        expect(requests_mock.called).to_be_true()
        requests_mock.assert_called_once_with(
            "http://localhost:2368/worker/%s/complete/000" % str(worker.uuid)
        )

    def test_do_work_without_next_job(self):
        worker = holmes.worker.HolmesWorker()

        job = None
        worker._load_next_job = Mock(return_value=job)
        worker._ping_api = Mock(return_value=True)
        worker._start_job = Mock()
        worker._complete_job = Mock()

        worker._do_work()

        expect(worker._start_job.called).to_be_false()
        expect(worker._complete_job.called).to_be_false()

    @gen_test
    def test_do_work_with_next_job(self):
        domain = yield DomainFactory.create()
        page = yield PageFactory.create(domain=domain)
        review = yield ReviewFactory.create(page=page)

        worker = holmes.worker.HolmesWorker()

        job = {"page": str(page.uuid), "review": str(review.uuid), "url": page.url}
        worker._load_next_job = Mock(return_value=job)
        worker._ping_api = Mock(return_value=True)
        worker._start_job = Mock()
        worker._complete_job = Mock()

        worker._do_work()

        expect(worker._start_job.called).to_be_true()
        expect(worker._complete_job.called).to_be_true()
