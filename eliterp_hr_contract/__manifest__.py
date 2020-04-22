# -*- coding: utf-8 -*-

{
    'name': "Módulo de Contratos Eliterp (RRHH)",
    'author': "Elitumdevelop S.A.",
    'category': "Personalization",
    'license': "LGPL-3",
    'version': "1.0",
    'depends': [
        'hr_contract',
        'eliterp_hr_employee'
    ],
    'data': [
        'data/data_contract.xml',
        'security/hr_contract_security.xml',
        'data/sequences.xml',
        'report/paperformat_reports.xml',
        'report/contract_reports.xml',
        'views/res_config_settings_views.xml',
        'views/contract_views.xml'
    ],
    'init_xml': [],
    'update_xml': [],
    'installable': True,
    'active': False,
}
