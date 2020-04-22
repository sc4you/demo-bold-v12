# -*- coding: utf-8 -*-

{
    'name': "Módulo de Nómina Eliterp",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'hr_payroll',
        'hr_payroll_account',
        'eliterp_payment',
        'eliterp_hr_contract',
        'eliterp_hr_holidays'
    ],
    'data': [
        'data/sequences.xml',
        'data/data_payroll.xml',
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        'report/payroll_reports.xml',
        'views/company_views.xml',
        'views/res_config_settings_views.xml',
        'views/salary_advance_views.xml',
        'views/payslip_views.xml',
        'views/payslip_run_views.xml',
        'views/provision_views.xml',
        'views/utility_views.xml',
        'views/hide_menus.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
