# -*- coding: utf-8 -*-

{
    'name': "Módulo Contable Eliterp",
    'summary': 'Módulo contable personalizado para la localización de Ecuador.',
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'product',
        'eliterp_chart_template',
        'account_accountant'
    ],
    'data': [
        'data/accountant_data.xml',
        'data/sequences.xml',
        'security/accountant_security.xml',
        'security/ir.model.access.csv',
        'views/accountant_views.xml',
        'views/period_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
