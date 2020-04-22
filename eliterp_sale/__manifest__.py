# -*- coding: utf-8 -*-

{
    'name': "Ventas Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_sri',
        'sale',
        'sale_enterprise',
        'sale_stock',
        'sale_management',
        'sales_team'
    ],
    'data': [
        'data/sequences.xml',
        'security/ir.model.access.csv',
        'report/report_order.xml',
        'views/partner_views.xml',
        'views/sale_order_views.xml',
        'views/sale_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
