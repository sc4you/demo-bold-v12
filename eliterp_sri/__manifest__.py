# -*- coding: utf-8 -*-

{
    'name': "Módulo del SRI Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_accountant'
    ],
    'data': [
        'security/sri_security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/sri.payment.forms.csv',
        'data/sri.proof.support.csv',
        'data/sri.authorized.vouchers.csv',
        'data/account.fiscal.position.csv',
        'data/sri_data.xml',
        'views/sri_views.xml',
        'views/users_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_invoice_views.xml',
        'views/account_invoice_refund_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
