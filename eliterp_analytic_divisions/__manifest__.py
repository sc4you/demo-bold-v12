# -*- coding: utf-8 -*-

{
    'name': "Módulo de Divisiones Analíticas Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'account'
    ],
    'data': [
        'data/analytic_divisions_data.xml',
        'security/analytic_divisions_security.xml',
        'security/ir.model.access.csv',
        'views/company_division_views.xml',
        'views/project_views.xml',
        'views/invoice_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
