# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_wage = fields.Float(
        'Sueldo básico unficado',
        default=394,
        default_model='hr.contract',
        config_parameter='contract.minimum_wage'
    )

    default_test_days = fields.Integer(
        'Días de período de prueba',
        default_model='hr.contract',
        default=90
    )

    @api.multi
    def set_values(self):
        res = super(ConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('contract.minimum_wage', self.default_wage)
        return res
