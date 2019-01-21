# -*- encoding: utf-8 -*-

from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils.translation import ugettext as _

from geotrek.common.models import Theme
from geotrek.common.parsers import (TourInSoftParser, GlobalImportError,
                                    RowImportError, ValueImportError)
from geotrek.tourism.models import InformationDesk, InformationDeskType, TouristicContent
from geotrek.trekking.models import Trek, Practice, TrekRelationship, POI, Accessibility
from geotrek.trekking.parsers import TrekParser
from geotrek.zoning.parsers import CityParser
from geotrek.tourism.parsers import HebergementsSitraParser


def add_http(url):
    if url and '://' not in url:
        return 'http://' + url
    return url


class CG44TourInSoftParser(TourInSoftParser):
    base_url = 'http://cdt44.media.tourinsoft.eu/upload/'
    delete_attachments = True


class CG44TouristicContentParser(CG44TourInSoftParser):
    model = TouristicContent
    eid = 'eid'
    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description_teaser': 'DescriptifSynthetique',
        'description': 'Descriptif',
        'contact': ('Adresse1', 'Adresse1Suite', 'Adresse2', 'Adresse3', 'CodePostal', 'Commune', 'Cedex'),
        'email': 'CommMail',
        'website': 'CommWeb',
        'geom': ('GmapLatitude', 'GmapLongitude'),
    }
    natural_keys = {
        'category': 'label',
        'type1': 'label',
        'type2': 'label',
    }

    def filter_description(self, src, val):
        return val or ""  # transform null to blank

    def filter_description_teaser(self, src, val):
        return val or ""  # transform null to blank

    def filter_contact(self, src, val):
        (Adresse1, Adresse1Suite, Adresse2, Adresse3, CodePostal, Commune, Cedex) = val
        lines = [line for line in [
            ' '.join([part for part in [Adresse1, Adresse1Suite] if part]),
            Adresse2,
            Adresse3,
            ' '.join([part for part in [CodePostal, Commune, Cedex] if part]),
        ] if line]
        return '<br>'.join(lines)

    def filter_geom(self, src, val):
        lat, lng = val
        if lng == '' or lat == '':
            raise RowImportError(u"Required value for fields 'GmapLatitude' and 'GmapLongitude'.")
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom

    def filter_website(self, src, val):
        return add_http(val)


class CG44POIParser(CG44TourInSoftParser):
    model = POI
    eid = 'eid'
    fields = {
        'eid': 'SyndicObjectID',
        'name': 'SyndicObjectName',
        'description': ('Adresse1', 'Adresse1Suite', 'Adresse2', 'Adresse3', 'CodePostal', 'Commune', 'Cedex', 'CommMail', 'CommWeb'),
        'geom': ('GmapLatitude', 'GmapLongitude'),
    }
    natural_keys = {
        'type': 'label',
    }

    def filter_description(self, src, val):
        (Adresse1, Adresse1Suite, Adresse2, Adresse3, CodePostal, Commune, Cedex, CommMail, CommWeb) = val
        CommWeb = add_http(CommWeb)
        lines = [line for line in [
            ' '.join([part for part in [Adresse1, Adresse1Suite] if part]),
            Adresse2,
            Adresse3,
            ' '.join([part for part in [CodePostal, Commune, Cedex] if part]),
            u'<a href="mailto:{email}">{email}</a>'.format(email=CommMail) if CommMail else '',
            u'<a href="{url}">{url}</a>'.format(url=CommWeb) if CommWeb else '',
        ] if line]
        return '<br>'.join(lines)

    def filter_geom(self, src, val):
        lat, lng = val
        if lng == '' or lat == '':
            raise RowImportError(u"Required value for fields 'GmapLatitude' and 'GmapLongitude'.")
        geom = Point(float(lng), float(lat), srid=4326)  # WGS84
        geom.transform(settings.SRID)
        return geom


class CG44HebergementParser(CG44POIParser):
    label = u"Hebergements"
    url = 'http://wcf.tourinsoft.com/Syndication/cdt44/b94de37c-b0b1-414f-9559-53510be235dc/Objects'
    constant_fields = {
        'type': u"Hébergement",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }



class CG44RestaurationParser(CG44POIParser):
    download_attachments = True
    label = u"Restauration"
    url = 'http://wcf.tourinsoft.com/Syndication/cdt44/e079fe27-11ad-4389-ac67-34bda49cc324/Objects'
    constant_fields = {
        'type': u"Restauration",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44AVoirParser(CG44TouristicContentParser):
    label = u"A voir"
    url = 'http://wcf.tourinsoft.com/Syndication/cdt44/99c93523-4194-428c-97f4-56bd3f774982/Objects'
    constant_fields = {
        'category': u"A voir",
        'published': True,
    }
    # m2m_fields = {
    #     'type1': 'ObjectTypeName',
    # }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44AFaireParser(CG44TouristicContentParser):
    label = u"A faire"
    url = 'http://wcf.tourinsoft.com/Syndication/cdt44/7b171134-26bf-485f-b1e1-65f9f4187c6f/Objects'
    constant_fields = {
        'category': u"A faire",
        'published': True,
    }
    non_fields = {
        'attachments': 'Photos',
    }


class CG44LADTrekParser(TourInSoftParser):
    label = u"Descriptif des itinéraires"
    url = 'http://wcf.tourinsoft.com/Syndication/cdt44/31cd7100-e547-4780-8292-53dabbc884a9/Objects'
    base_url = 'http://cdt44.media.tourinsoft.eu/upload/'
    model = Trek
    update_only = True
    warn_on_missing_fields = True
    eid = 'eid2'
    duplicate_eid_allowed = True
    information_desk_type_name = u"Office du tourisme"
    fields = {
        'eid2': 'SyndicObjectID',
        'description_teaser': 'DescriptifSynthetique',
        'description': 'Descriptif',
    }
    m2m_fields = {
        'information_desks': ('CommTel', 'NomGest', 'CommMail', 'CommWeb'),
    }
    non_fields = {
        'attachments': 'Photos',
    }

    def start(self):
        super(CG44LADTrekParser, self).start()
        try:
            self.information_desk_type = InformationDeskType.objects.get(label=self.information_desk_type_name)
        except InformationDeskType.DoesNotExist:
            raise GlobalImportError(u"Information desk type '{name}' does not exists in Geotrek-Admin. Please add it.".format(name=self.information_desk_type_name))

    def filter_information_desks(self, src, val):
        tel, contact, mail, web = val
        if not contact:
            return []
        information_desk = self.obj.information_desks.first()
        if not information_desk:
            information_desk = InformationDesk(type=self.information_desk_type)
        information_desk.phone = tel
        information_desk.name = contact
        information_desk.email = mail
        information_desk.website = add_http(web)
        information_desk.save()
        return [information_desk]


class CG44TrekParser(TrekParser):
    warn_on_missing_fields = True
    eid = 'eid'
    fields = {
        'eid': 'NUM_OBJ',
        'name': 'ALIAS',
        'duration': ('PARCOURS', 'USAGES'),
        'difficulty': 'DIFFICULTE',
        'eid2': 'GENCOMM',
        'route': 'CARAC',
        'practice': 'USAGES',
        'advice': 'ItiFermetureTemporaire',
        'geom': 'geom',
    }
    m2m_fields = {
        'themes': 'AVIS',
        'accessibilities': 'USAGES',
    }
    non_fields = {
        'related_treks': 'LIAISONS',
    }
    field_options = {
        'route': {'mapping': {u"Boucle": u"Boucle (PR)", u"Itinerance": u"Itinérance (GR/GRP)"}, 'partial': True},
        'themes': {'mapping': {u"VIGNOBLE": u"Vignoble", u"LITTORAL": u"Littoral", u"FLEUVE ET RIVIERE": u"Fleuve et rivière", u"CAMPAGNE": u"Campagne", u"MARAIS": u"Marais", u"PATRIMOINE": u"Patrimoine", u"INCONTOURNABLE": u"Incontournables"}},
    }
    ALIAS_to_pk = {}
    relationships = []

    def start(self):
        super(CG44TrekParser, self).start()
        self.to_delete = set(Trek.objects.filter(practice__name=self.practice).values_list('pk', flat=True))

    def end(self):
        for pk_a, name_b in self.relationships:
            try:
                pk_b = self.ALIAS_to_pk[name_b]
            except KeyError:
                self.add_warning(u"Bad value '{name}' for field FIRST_LIAI (separated by {separator}). No trek with this name in data to import.".format(name=name_b, separator=self.separator))
                continue
            TrekRelationship.objects.get_or_create(
                trek_a=Trek.objects.get(pk=pk_a),
                trek_b=Trek.objects.get(pk=pk_b),
                is_circuit_step=True
            )
        super(CG44TrekParser, self).end()

    def parse_row(self, row):
        super(CG44TrekParser, self).parse_row(row)
        if self.obj:
            self.ALIAS_to_pk[row['ALIAS']] = self.obj.pk

    def filter_name(self, src, val):
        return val.split(':', 1)[1].strip()

    def filter_practice(self, src, val):
        val = [subval.strip() for subval in val.split(self.separator)]
        if self.practice not in val:
            raise RowImportError(u"Bad value '{val}' for field {src} (separated by '{separator}'). Should contain '{practice}'.".format(val=val, src=src, separator=self.separator, practice=self.practice))
        return self.filter_fk(src, self.practice, Practice, 'name')

    def filter_accessibilities(self, src, val):
        val = [subval.strip() for subval in val.split(self.separator) if subval.strip() != self.practice]
        return self.filter_m2m(src, ' + '.join(val), Accessibility, 'name')

    def filter_duration(self, src, val):
        duration, usages = val
        first_usage = usages.split(self.separator)[0].strip()
        if duration == '?':
            return 0
        elif first_usage == self.practice:
            return super(CG44TrekParser, self).filter_duration(src, duration)
        else:
            raise ValueImportError(u"Ignore duration since it does not correspond to practice")

    def save_related_treks(self, src, val):
        if not val:
            return
        val = val.split(self.separator)
        self.relationships += [(self.obj.pk, name.strip()) for name in val]

    def concat(self, a, b, second=False):
        """Concatenate two linestrings trying to find the right direction for the
        second one (and for the first one too if second is true"""
        if a is None and b is None:
            return None
        elif a is None:
            return b
        elif b is None:
            return a
        if second:
            start_a = Point(a[0])
            end_a = Point(a[-1])
            start_b = Point(b[0])
            end_b = Point(b[-1])
            reverse = {
                start_a.distance(start_b): True,
                start_a.distance(end_b): True,
                end_a.distance(start_b): False,
                end_a.distance(end_b): False,
            }
            if reverse[min(reverse.keys())]:
                a.reverse()
        end_a = Point(a[-1])
        start_b = Point(b[0])
        end_b = Point(b[-1])
        d1 = end_a.distance(start_b)
        d2 = end_a.distance(end_b)
        if d2 < d1:
            b.reverse()
        if min(d1, d2) > 5:
            self.add_warning(_(u"Not contiguous segment ({distance} m)").format(distance=int(min(d1, d2))))
        return a + b

    def next_row(self):
        rows = list(super(CG44TrekParser, self).next_row())
        rows = [row for row in rows if row['GEOM'] is not None]
        rows.sort(key=lambda row: (row['NUM_OBJ'], row['NUM_ORDRE']))
        self.nb = len(set([row['NUM_OBJ'] for row in rows]))
        prev = None
        second = False

        for row in rows:
            if prev is None:
                prev = row
                line = row['GEOM']
                second = True
            elif prev['NUM_OBJ'] == row['NUM_OBJ']:
                line = self.concat(line, row['GEOM'], second)
                second = False
            else:
                prev['GEOM'] = line
                yield prev
                prev = row
                line = row['GEOM']
                second = True
        if rows:
            prev['GEOM'] = line
            yield prev


class CG44PedestreTrekParser(CG44TrekParser):
    label = u"Itinéraires pédestre"
    practice = u"Pédestre"

    def filter_eid(self, src, val):
        return 'P-' + str(val)


class CG44VTTTrekParser(CG44TrekParser):
    label = u"Itinéraires VTT"
    practice = u"VTT"

    def filter_eid(self, src, val):
        return 'V-' + str(val)


class CG44EquestreTrekParser(CG44TrekParser):
    label = u"Itinéraires équestres"
    practice = u"Equestre"

    def filter_eid(self, src, val):
        return 'E-' + str(val)


class CG44AVeloTrekParser(TrekParser):
    label = u"Itinéraires vélo"
    warn_on_missing_fields = True
    eid = 'eid'
    fields = {
        'eid': 'ID_LOCAL',
        'name': 'INTITULE',
        'practice': 'USAGE',
        'duration': 'DUREE',
        'difficulty': 'NIVEAU',
        'route': 'TYPE',
        'eid2': 'ID_LAD',
        'geom': 'geom',
    }
    m2m_fields = {
        'themes': ('THEME', 'PRIORITE'),
    }
    non_fields = {
        'related_treks': ('ID_ITI', 'ORDRE_ETAP'),
    }
    field_options = {
        'difficulty': {'mapping': {1: u"Facile", 2: u"Moyen", 3: u"Difficile"}},
        'route': {'mapping': {1: u"Boucle", 2: u"Itinérance"}},
    }
    relationships = {}

    def end(self):
        for treks in self.relationships.itervalues():
            for etap, trek_a in treks.items():
                trek_b = treks.get(etap + 1)
                if not trek_b:
                    continue
                TrekRelationship.objects.get_or_create(
                    trek_a=trek_a,
                    trek_b=trek_b,
                    is_circuit_step=True
                )
        super(CG44AVeloTrekParser, self).end()

    def filter_eid(self, src, val):
        return 'C-' + str(val)

    def filter_themes(self, src, val):
        val_theme, val_priorite = val
        val_theme = str(val_theme)
        val_theme = self.filter_m2m(src, val_theme, Theme, 'label', {'1': u"Vignoble", '2': u"Littoral", '3': u"Fleuve et rivière", '4': u"Campagne", '5': u"Marais", '6': u"Patrimoine", '7': u"Incontournables"})
        if val_priorite == 1:
            try:
                val_priorite = [Theme.objects.get(label='Incontournables')]
            except Theme.DoesNotExist:
                self.add_warning(u"Theme 'Incontournables' does not exists in Geotrek-Admin. Please add it.")
                val_priorite = []
        else:
            val_priorite = []
        return val_theme + val_priorite

    def save_related_treks(self, src, val):
        iti, etap = val
        if not iti or etap == 0:
            return
        self.relationships.setdefault(iti, {})
        self.relationships[iti][int(etap)] = self.obj


class CG44PedestreDeleteTrekParser(CG44PedestreTrekParser):
    label = u"Itinéraires pédestre (avec suppression)"
    delete = True


class CG44VTTDeleteTrekParser(CG44VTTTrekParser):
    label = u"Itinéraires VTT (avec suppression)"
    delete = True


class CG44EquestreDeleteTrekParser(CG44EquestreTrekParser):
    label = u"Itinéraires équestres (avec suppression)"
    delete = True


class CG44AVeloDeleteTrekParser(CG44AVeloTrekParser):
    label = u"Itinéraires vélo (avec suppression)"
    delete = True


class CG44CityParser(CityParser):
    label = u"Communes"
    warn_on_missing_fields = True
    fields = {
        'code': 'CODE_INSEE',
        'name': 'NOM',
        'geom': 'geom',
    }

class HebergementParser(HebergementsSitraParser):
    label = u"Hebergements PNE APIDAE"
    api_key = '4VcrzLCH'
    project_id = 1510
    selection_id = 37078
    source = ['Apidae']
    portal = ['Grand Tour des Ecrins']
    constant_fields = {
    }
    non_fields = {
        'attachments': 'illustrations',
    }
# override this method to dont republish unpublished objects
    def parse_obj(self, row, operation):
        if not self.obj.pk:
            self.obj.published = True
        super(HebergementParser, self).parse_obj(row, operation)