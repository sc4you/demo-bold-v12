# -*- coding: utf-8 -*-

{
    'name': "Módulo de Depósitos bancarios Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_payment_checks'
    ],
    'data': [
        'data/sequences.xml',
        'security/deposit_security.xml',
        'security/ir.model.access.csv',
        'report/deposit_reports.xml',
        'views/deposit_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
