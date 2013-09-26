#!/usr/bin/python
# -*- coding: utf-8 -*-

from cow.server import Server
from cow.plugins.motorengine_plugin import MotorEnginePlugin

from holmes.handlers.worker import WorkerPingHandler


def main():
    HolmesApiServer.run()


class HolmesApiServer(Server):
    def get_handlers(self):
        handlers = [
            ('/worker/ping', WorkerPingHandler),
        ]

        return tuple(handlers)

    def get_plugins(self):
        return [
            MotorEnginePlugin,
        ]


if __name__ == '__main__':
    main()
