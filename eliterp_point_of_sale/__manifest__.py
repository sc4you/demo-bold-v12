# -*- coding: utf-8 -*-

{
    'name': "Módulo Punto de venta Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_sri_electronic_voucher',
        'point_of_sale'
    ],
    'data': [
        'data/data_pos.xml',
        'data/data_resources.xml',
        'security/ir.model.access.csv',
        'views/config_views.xml',
        'views/order_views.xml',
        'views/pos_views.xml'
    ],
    'qweb': [
        'static/src/xml/pos.xml',
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
