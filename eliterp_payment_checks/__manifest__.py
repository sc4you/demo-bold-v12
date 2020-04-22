# -*- coding: utf-8 -*-

{
    'name': "Módulo de Cheques Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_payment',
        'account_check_printing'
    ],
    'data': [
        'data/checks_data.xml',
        'data/sequences.xml',
        'report/payment_reports.xml',
        'views/journal_views.xml',
        'views/payment_checks_views.xml',
        'views/payment_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
