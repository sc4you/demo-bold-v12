# -*- coding: utf-8 -*-

{
    'name': "Módulo de Retenciones Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_sri'
    ],
    'data': [
        'data/retention_data.xml',
        'data/sequences.xml',
        'security/retention_security.xml',
        'security/ir.model.access.csv',
        'views/company_views.xml',
        'views/sri_views.xml',
        'views/partner_views.xml',
        'views/retention_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
