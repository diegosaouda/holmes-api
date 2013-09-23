#!/usr/bin/python
# -*- coding: utf-8 -*-


from preggy import expect
from mock import patch
from os.path import abspath, dirname, join

import holmes.worker
from tests.base import ApiTestCase


class WorkerTestCase(ApiTestCase):
    root_path = abspath(join(dirname(__file__), ".."))

    @patch('holmes.worker.HolmesWorker')
    def test_worker_main_function(self, worker_mock):
        holmes.worker.main()
        expect(worker_mock().run.called).to_be_true()

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
        expect(worker.config.VALIDATORS).to_equal(set())

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

