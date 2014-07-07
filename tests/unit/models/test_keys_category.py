#!/usr/bin/python
# -*- coding: utf-8 -*-

from preggy import expect

from holmes.models import KeysCategory

from tests.unit.base import ApiTestCase
from tests.fixtures import KeysCategoryFactory


class TestKeysCategory(ApiTestCase):

    def test_can_create_key_category(self):
        category = KeysCategoryFactory.create()

        expect(category.id).not_to_be_null()
        expect(category.name).not_to_be_null()

        loaded = self.db.query(KeysCategory).get(category.id)

        expect(str(loaded)).to_be_like('%s' % category.name)
        expect(loaded.id).to_equal(category.id)
        expect(loaded.name).to_equal(category.name)

    def test_can_convert_keys_category_to_dict(self):
        category = KeysCategoryFactory.create()

        category_dict = category.to_dict()

        expect(category_dict).to_be_like({
            'name': str(category.name)
        })

    def test_can_get_or_create(self):
        # Create
        cat1 = KeysCategory.get_or_create(self.db, 'SEO')
        expect(cat1.name).to_equal('SEO')

        # Get
        cat2 = KeysCategory.get_or_create(self.db, 'SEO')
        expect(cat1.id).to_equal(cat2.id)

    def test_get_by_name(self):
        category = KeysCategoryFactory.create(name='HOLMES')

        loaded_category = KeysCategory.get_by_name(self.db, 'HOLMES')

        expect(category).to_equal(loaded_category)
        expect(loaded_category.name).to_equal('HOLMES')

    def test_get_by_id(self):
        no_category = KeysCategory.get_by_id(self.db, -1)
        expect(no_category).to_be_null()

        category = KeysCategoryFactory.create(name='HOLMES')

        loaded_category = KeysCategory.get_by_id(self.db, category.id)

        expect(category).to_equal(loaded_category)
        expect(loaded_category.name).to_equal('HOLMES')
        expect(loaded_category.id).to_equal(category.id)
