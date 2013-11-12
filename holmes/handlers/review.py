#!/usr/bin/python
# -*- coding: utf-8 -*-

from datetime import datetime
from uuid import UUID

import logging
from tornado import gen
from motorengine import Q

from holmes.models import Review
from holmes.handlers import BaseHandler


class BaseReviewHandler(BaseHandler):
    def _parse_uuid(self, uuid):
        try:
            return UUID(uuid)
        except ValueError:
            return None


class ReviewHandler(BaseReviewHandler):
    @gen.coroutine
    def get(self, page_uuid, review_uuid):
        review = None
        if self._parse_uuid(review_uuid):
            review = yield Review.objects.get(uuid=review_uuid)

        if not review:
            self.set_status(404, 'Review with uuid of %s not found!' % review_uuid)
            self.finish()
            return

        yield review.load_references(['page', 'domain'])

        if review.completed_date:
            completed_data_iso = review.completed_date.isoformat()
        else:
            completed_data_iso = None

        result = review.to_dict()
        result.update({
            'violationPoints': review.get_violation_points(),
            'violationCount': review.violation_count,
            'completedDateISO': completed_data_iso
        })

        self.write_json(result)
        self.finish()


class CompleteReviewHandler(BaseReviewHandler):
    @gen.coroutine
    def post(self, page_uuid, review_uuid):
        review = None
        if self._parse_uuid(review_uuid):
            review = yield Review.objects.get(uuid=review_uuid)

        if not review:
            self.set_status(404, 'Review with uuid of %s not found!' % review_uuid)
            logging.debug('Review with uuid of %s not found!' % review_uuid)
            self.finish()
            return

        if review.is_complete:
            self.set_status(400, 'Review with uuid %s is already completed!' % review_uuid)
            logging.debug('Review with uuid %s is already completed!' % review_uuid)
            self.finish()
            return

        review.is_complete = True
        review.is_active = True
        review.completed_date = datetime.now()

        yield review.load_references(['page'])
        review.page.last_review = review
        review.page.last_review_date = review.completed_date
        yield review.page.save()
        yield review.save()

        self._remove_older_reviews_with_same_day(review)

        query = Q(page=review.page) & Q(uuid__ne=review_uuid)

        yield Review.objects.filter(query).update({
            Review.is_active: False
        })

        self.write('OK')
        self.finish()

    @gen.coroutine
    def _remove_older_reviews_with_same_day(self, review):
        dt = datetime.now()
        dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        query = Q(page=review.page) & Q(uuid__ne=review.uuid) & Q(created_date__gte=dt)
        yield Review.objects.filter(query).delete()


class LastReviewsHandler(BaseReviewHandler):
    @gen.coroutine
    def get(self):
        reviews = yield Review.get_last_reviews()

        reviews_json = []
        for review in reviews:
            yield review.load_references(['page', 'domain'])
            review_dict = review.to_dict()
            data = {
                'violationCount': review.violation_count,
                'completedDateISO': review.completed_date.isoformat()
            }
            review_dict.update(data)
            reviews_json.append(review_dict)

        self.write_json(reviews_json)
        self.finish()
