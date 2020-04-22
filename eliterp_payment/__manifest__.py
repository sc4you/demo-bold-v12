# -*- coding: utf-8 -*-

{
    'name': "Módulo de Pagos Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'payment',
        'eliterp_account_retention'
    ],
    'data': [
        'data/sequences.xml',
        'security/payment_security.xml',
        'security/ir.model.access.csv',
        'report/payment_reports.xml',
        'report/cashier_reports.xml',
        'views/payment_views.xml',
        'views/payment_special_views.xml',
        'views/pay_order_views.xml',
        'views/invoice_views.xml',
        'views/cashier_views.xml',
        'wizard/payment_cancel_views.xml',
        'wizard/cashier_wizard_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
