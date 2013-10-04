#!/usr/bin/python
# -*- coding: utf-8 -*-

from uuid import UUID

from tornado.web import RequestHandler
from tornado import gen
from ujson import dumps

from holmes.models import Review


class ReviewHandler(RequestHandler):
    def __parse_uuid(self, uuid):
        try:
            return UUID(uuid)
        except ValueError:
            return None

    @gen.coroutine
    def get(self, page_uuid, review_uuid):
        review = None
        if self.__parse_uuid(review_uuid):
            review = yield Review.objects.get(uuid=review_uuid)

        if not review:
            self.set_status(404, "Review with uuid of %s not found!" % review_uuid)
            self.finish()
            return

        yield review.load_references(['page'])
        yield review.page.load_references(['domain'])

        self.write(dumps(review.to_dict()))
        self.finish()
