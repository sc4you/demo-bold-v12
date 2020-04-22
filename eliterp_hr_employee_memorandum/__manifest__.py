# -*- coding: utf-8 -*-

{
    'name': "Memorándum's de Empleados Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_hr_employee',
        'mail'
    ],
    'data': [
        'data/sequences.xml',
        'security/ir.model.access.csv',
        'views/memorandum_views.xml',
        'views/employee_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
