# -*- coding: utf-8 -*-

{
    'name': "Inventario Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'product',
        'stock',
        'stock_account',
        'stock_account_enterprise',
        'stock_enterprise'
    ],
    'data': [
        'data/sequences.xml',
        'data/data_stock.xml',
        'data/email_templates.xml',
        'security/ir.model.access.csv',
        'report/report_deliveryslip.xml',
        'views/company_views.xml',
        'views/location_views.xml',
        'views/product_views.xml',
        'views/stock_account_views.xml',
        'views/quant_views.xml',
        'views/inventory_views.xml',
        'views/picking_views.xml',
        'views/scrap_views.xml',
        'views/stock_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
