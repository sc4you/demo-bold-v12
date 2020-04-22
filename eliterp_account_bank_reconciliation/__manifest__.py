# -*- coding: utf-8 -*-

{
    'name': "Módulo de Conciliación Bancaria Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_account_deposit'
    ],
    'data': [
        'data/sequences.xml',
        'security/account_bank_reconciliation_security.xml',
        'security/ir.model.access.csv',
        'report/account_bank_reconciliation_report.xml',
        'views/account_bank_reconciliation_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
