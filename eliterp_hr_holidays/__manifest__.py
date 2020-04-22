# -*- coding: utf-8 -*-

{
    'name': "Módulo de Ausencias Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'hr_holidays'
    ],
    'data': [
        'data/data_holidays.xml',
        'security/ir.model.access.csv',
        'report/holidays_reports.xml',
        'views/holidays_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
