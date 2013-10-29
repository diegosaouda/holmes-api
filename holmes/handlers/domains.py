#!/usr/bin/python
# -*- coding: utf-8 -*-

from tornado import gen
from motorengine import ASCENDING

from holmes.models import Domain, Page
from holmes.handlers import BaseHandler


class DomainsHandler(BaseHandler):

    @gen.coroutine
    def get(self):
        domains = yield Domain.objects.order_by(Domain.name, ASCENDING).find_all()
        violations_per_domain = yield Domain.get_violations_per_domain()
        pages_per_domain = yield Domain.get_pages_per_domain()

        if not domains:
            self.write("[]")
            self.finish()
            return

        result = []

        for domain in domains:
            result.append({
                "url": domain.url,
                "name": domain.name,
                "violationCount": violations_per_domain.get(domain._id, 0),
                "pageCount": pages_per_domain.get(domain._id, 0)
            })

        self.write_json(result)
        self.finish()


class DomainDetailsHandler(BaseHandler):

    @gen.coroutine
    def get(self, domain_name):
        domain = yield Domain.objects.get(name=domain_name)

        if not domain:
            self.set_status(404, 'Domain with name "%s" was not found!' % domain_name)
            self.finish()
            return

        page_count = yield domain.get_page_count()
        violation_count, violation_points = yield domain.get_violation_data()

        domain_json = {
            "name": domain.name,
            "url": domain.url,
            "pageCount": page_count,
            "violationCount": violation_count,
            "violationPoints": violation_points
        }

        self.write_json(domain_json)
        self.finish()


class DomainViolationsPerDayHandler(BaseHandler):

    @gen.coroutine
    def get(self, domain_name):
        domain = yield Domain.objects.get(name=domain_name)

        if not domain:
            self.set_status(404, 'Domain with name "%s" was not found!' % domain_name)
            self.finish()
            return

        violations_per_day = yield domain.get_violations_per_day()

        domain_json = {
            "name": domain.name,
            "url": domain.url,
            "violations": violations_per_day
        }

        self.write_json(domain_json)
        self.finish()


class DomainReviewsHandler(BaseHandler):

    @gen.coroutine
    def get(self, domain_name):
        domain = yield Domain.objects.get(name=domain_name)

        if not domain:
            self.set_status(404, 'Domain with name "%s" was not found!' % domain_name)
            self.finish()
            return

        reviews = yield domain.get_active_reviews()

        result = {
            'domainName': domain.name,
            'domainURL': domain.url,
            'pages': [],
            'pagesWithoutReview': []
        }

        for review in reviews:
            yield review.page.load_references()

            result['pages'].append({
                "url": review.page.url,
                "uuid": str(review.page.uuid),
                "completedDate": review.completed_date.isoformat()
            })

        pages = yield Page.objects.filter(domain=domain, last_review__is_null=True).find_all()
        for page in pages:
            result['pagesWithoutReview'].append({
                'uuid': str(page.uuid),
                'url': page.url
            })

        self.write_json(result)
        self.finish()
