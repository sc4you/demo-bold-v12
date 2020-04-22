# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    advance_percentage = fields.Integer(
        string='Porcentaje de quincena'
    )

    @api.model
    def get_values(self):
        res = super(ConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            advance_percentage=int(params.get_param('eliterp_hr_payroll.advance_percentage', default=50))
        )
        return res

    @api.multi
    def set_values(self):
        super(ConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("eliterp_hr_payroll.advance_percentage",
                                                         self.advance_percentage)
