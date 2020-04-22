# -*- coding: utf-8 -*-

{
    'name': "Módulo de Compras Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'purchase',
        'eliterp_stock'
    ],
    'data': [
        'data/sequences.xml',
        'data/purchase_data.xml',
        'report/purchase_reports.xml',
        'views/product_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_invoice_views.xml',
        'views/purchase_views.xml'

    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
