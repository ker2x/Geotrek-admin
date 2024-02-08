
from unittest import mock, skipIf

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from geotrek.common.models import Attachment, FileType
from geotrek.common.tests.mixins import GeotrekParserTestMixin
from geotrek.outdoor.models import Course, OrderedCourseChild, Practice, Rating, RatingScale, Sector, Site
from geotrek.outdoor.parsers import GeotrekCourseParser, GeotrekSiteParser


class TestGeotrekSiteParser(GeotrekSiteParser):
    url = "https://test.fr"
    provider = 'geotrek1'
    field_options = {
        'themes': {'create': True},
        'geom': {'required': True},
        'labels': {'create': True},
        'source': {'create': True},
        'managers': {'create': True},
        'structure': {'create': True}
    }


class TestGeotrekCourseParser(GeotrekCourseParser):
    url = "https://test.fr"
    provider = 'geotrek2'
    field_options = {
        'themes': {'create': True},
        'geom': {'required': True},
        'structure': {'create': True}
    }


@override_settings(MODELTRANSLATION_DEFAULT_LANGUAGE="fr")
@skipIf(settings.TREKKING_TOPOLOGY_ENABLED, 'Test without dynamic segmentation only')
class OutdoorGeotrekParserTests(GeotrekParserTestMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.filetype = FileType.objects.create(type="Photographie")

    @mock.patch('requests.get')
    @mock.patch('requests.head')
    def test_create_sites_and_courses(self, mocked_head, mocked_get):
        self.mock_time = 0
        self.mock_json_order = [('outdoor', 'theme.json'),
                                ('outdoor', 'label.json'),
                                ('outdoor', 'source.json'),
                                ('outdoor', 'organism.json'),
                                ('outdoor', 'structure.json'),
                                ('outdoor', 'outdoor_sector.json'),
                                ('outdoor', 'outdoor_practice.json'),
                                ('outdoor', 'outdoor_ratingscale.json'),
                                ('outdoor', 'outdoor_rating.json'),
                                ('outdoor', 'outdoor_sitetype.json'),
                                ('outdoor', 'outdoor_site_ids.json'),
                                ('outdoor', 'outdoor_site.json'),
                                ('outdoor', 'theme.json'),
                                ('outdoor', 'label.json'),
                                ('outdoor', 'source.json'),
                                ('outdoor', 'organism.json'),
                                ('outdoor', 'structure.json'),
                                ('outdoor', 'outdoor_sector.json'),
                                ('outdoor', 'outdoor_practice.json'),
                                ('outdoor', 'outdoor_ratingscale.json'),
                                ('outdoor', 'outdoor_rating.json'),
                                ('outdoor', 'outdoor_coursetype.json'),
                                ('outdoor', 'outdoor_course_ids.json'),
                                ('outdoor', 'outdoor_course.json')]

        # Mock GET
        mocked_get.return_value.status_code = 200
        mocked_get.return_value.json = self.mock_json
        mocked_get.return_value.content = b''
        mocked_head.return_value.status_code = 200

        call_command('import', 'geotrek.outdoor.tests.test_parsers.TestGeotrekSiteParser', verbosity=0)
        self.assertEqual(Site.objects.count(), 6)
        self.assertEqual(Sector.objects.count(), 2)
        self.assertEqual(RatingScale.objects.count(), 1)
        self.assertEqual(Rating.objects.count(), 3)
        self.assertEqual(Practice.objects.count(), 1)
        site = Site.objects.get(name_fr="Racine", name_en="Root")
        self.assertEqual(site.published, True)
        self.assertEqual(site.published_fr, True)
        self.assertEqual(site.published_en, True)
        self.assertEqual(site.published_it, False)
        self.assertEqual(site.published_es, False)
        self.assertEqual(str(site.practice.sector), 'Vertical')
        self.assertEqual(str(site.practice), 'Escalade')
        self.assertEqual(str(site.labels.first()), 'Label fr')
        self.assertEqual(site.ratings.count(), 3)
        self.assertEqual(str(site.ratings.first()), 'Cotation : 3+')
        self.assertEqual(site.ratings.first().description, 'Une description')
        self.assertEqual(site.ratings.first().order, 302)
        self.assertEqual(site.ratings.first().color, '#D9D9D8')
        self.assertEqual(str(site.ratings.first().scale), 'Cotation (Escalade)')
        self.assertEqual(str(site.type), 'Ecole')
        self.assertEqual(str(site.type.practice), 'Escalade')
        self.assertAlmostEqual(site.geom[0][0][0][0], 970023.8976707931, places=5)
        self.assertAlmostEqual(site.geom[0][0][0][1], 6308806.903248067, places=5)
        self.assertAlmostEqual(site.geom[0][0][1][0], 967898.282139539, places=5)
        self.assertAlmostEqual(site.geom[0][0][1][1], 6358768.657410889, places=5)
        self.assertEqual(str(site.labels.first()), "Label fr")
        self.assertEqual(str(site.source.first()), "Source")
        self.assertEqual(str(site.themes.first()), "Test thème fr")
        self.assertEqual(str(site.managers.first()), "Organisme")
        self.assertEqual(str(site.structure), "Test structure")
        self.assertEqual(site.description_teaser, "Test fr")
        self.assertEqual(site.description_teaser_en, "Test en")
        self.assertEqual(site.description, "Test descr fr")
        self.assertEqual(site.description_en, "Test descr en")
        self.assertEqual(site.advice, "Test reco fr")
        self.assertEqual(site.accessibility, "Test access fr")
        self.assertEqual(site.period, "Test périod fr")
        self.assertEqual(site.orientation, ['NE', 'S'])
        self.assertEqual(site.ambiance, "Test ambiance fr")
        self.assertEqual(site.ambiance_en, "Test ambiance en")
        self.assertEqual(site.wind, ['N', 'E'])
        self.assertEqual(str(site.structure), 'Test structure')
        # TODO ; self.assertEqual(site.information_desks.count(), 1)
        # TODO : self.assertEqual(site.weblink.count(), 1)
        # TODO : self.assertEqual(site.excluded_pois.count(), 1)
        self.assertEqual(site.eid, "57a8fb52-213d-4dce-8224-bc997f892aae")
        self.assertEqual(Attachment.objects.filter(object_id=site.pk).count(), 1)
        attachment = Attachment.objects.filter(object_id=site.pk).first()
        self.assertIsNotNone(attachment.attachment_file.url)
        self.assertEqual(attachment.legend, 'Arrien-en-Bethmale, vue du village')
        child_site = Site.objects.get(name_fr="Noeud 1", name_en="Node")
        self.assertEqual(child_site.parent, site)

        call_command('import', 'geotrek.outdoor.tests.test_parsers.TestGeotrekCourseParser', verbosity=0)
        self.assertEqual(Course.objects.count(), 7)
        course = Course.objects.get(name_fr="Feuille 1", name_en="Leaf 1")
        self.assertEqual(str(course.type), 'Type 1')
        self.assertEqual(course.published, True)
        self.assertEqual(course.published_fr, True)
        self.assertEqual(course.published_en, True)
        self.assertEqual(course.published_it, False)
        self.assertEqual(course.published_es, False)
        self.assertEqual(course.ratings.count(), 1)
        self.assertEqual(str(course.ratings.first()), 'Cotation : 3+')
        self.assertEqual(course.ratings.first().description, 'Une description')
        self.assertEqual(course.ratings.first().order, 302)
        self.assertEqual(course.ratings.first().color, '#D9D9D8')
        self.assertEqual(str(course.ratings.first().scale), 'Cotation (Escalade)')
        self.assertAlmostEqual(course.geom.coords[0][0], 994912.1442530667, places=5)
        self.assertAlmostEqual(course.geom.coords[0][1], 6347387.846494712, places=5)
        self.assertEqual(str(course.structure), "Test structure")
        self.assertEqual(course.description, "Test descr fr")
        self.assertEqual(course.description_en, "Test descr en")
        self.assertEqual(course.ratings_description, "Test descr fr")
        self.assertEqual(course.ratings_description_en, "Test descr en")
        self.assertEqual(course.equipment, "Test équipement fr")
        self.assertEqual(course.equipment_en, "Test équipement en")
        self.assertEqual(course.gear, "Test matériel fr")
        self.assertEqual(course.gear_en, "Test matériel en")
        self.assertEqual(course.advice, "Test reco fr")
        self.assertEqual(course.duration, 100)
        self.assertEqual(course.height, 100)
        self.assertEqual(course.accessibility, "Test access fr")
        self.assertEqual(str(course.structure), 'Test structure')
        # TODO : self.assertEqual(course.excluded_pois.count(), 1)
        self.assertEqual(course.eid, "840f4cf7-dbe0-4aa1-835f-c1219c45dd7a")
        self.assertEqual(Attachment.objects.filter(object_id=course.pk).count(), 1)
        attachment = Attachment.objects.filter(object_id=course.pk).first()
        self.assertIsNotNone(attachment.attachment_file.url)
        self.assertEqual(attachment.legend, 'Arrien-en-Bethmale, vue du village')
        parent_site = Site.objects.get(name_fr="Noeud 2 bis")
        self.assertEqual(course.parent_sites.count(), 1)
        self.assertEqual(course.parent_sites.first(), parent_site)
        self.assertEqual(str(course.parent_sites.first().practice), 'Escalade')
        child_course_1 = Course.objects.get(name="Step 1")
        child_course_2 = Course.objects.get(name="Step 2")
        child_course_3 = Course.objects.get(name="Step 3")
        self.assertTrue(OrderedCourseChild.objects.filter(parent=course, child=child_course_1, order=0).exists())
        self.assertTrue(OrderedCourseChild.objects.filter(parent=course, child=child_course_2, order=1).exists())
        self.assertTrue(OrderedCourseChild.objects.filter(parent=course, child=child_course_3, order=2).exists())
