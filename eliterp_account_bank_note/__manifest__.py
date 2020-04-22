# -*- coding: utf-8 -*-

{
    'name': "Módulo de Notas Bancarias Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_accountant'
    ],
    'data': [
        'data/sequences.xml',
        'security/bank_note_security.xml',
        'security/ir.model.access.csv',
        'views/bank_note_views.xml',
        'wizard/bank_note_cancel_views.xml',
        'report/bank_note_report.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
