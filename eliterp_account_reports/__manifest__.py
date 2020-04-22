# -*- coding: utf-8 -*-

{
    'name': "Reportes Contables Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_accountant',
        'account_reports'
    ],
    'data': [
        'wizard/reports_wizard_views.xml',
        'views/reports_views.xml',
        'report/reports.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
