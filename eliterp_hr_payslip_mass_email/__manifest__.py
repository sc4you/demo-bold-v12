# -*- coding: utf-8 -*-

{
    'name': "Envío de Roles a Empleados Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'eliterp_hr_payroll'
    ],
    'data': [
        'data/data.xml',
        'data/mail_template.xml',
        'wizard/payslip_mass_mail_wizard_views.xml',
        'views/payslip_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
