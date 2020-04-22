# -*- coding: utf-8 -*-

{
    'name': "Módulo Base Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'base_setup',
        'base_import',
        'base',
        'mail',
        'web'
    ],
    'data': [
        'security/base_security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/res.country.state.csv',
        'data/res.canton.csv',
        'data/res.parish.csv',
        'views/assets.xml',
        'views/company_views.xml',
        'report/layout_report.xml',
        'report/paperformat_report.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
