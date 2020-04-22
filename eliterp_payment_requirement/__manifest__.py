# -*- coding: utf-8 -*-

{
    'name': "Módulo de Requerimientos de Pago Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_start',
        'eliterp_payment',
        'eliterp_hr_employee'
    ],
    'data': [
        'data/sequences.xml',
        'security/payment_requirement_security.xml',
        'security/ir.model.access.csv',
        'report/payment_requirement_report.xml',
        'views/payment_requirement_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
