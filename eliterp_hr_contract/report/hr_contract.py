# -*- coding: utf-8 -*-


from odoo import api, fields, models

class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def _get_wage_letters(self):
        return self.env['res.function']._get_amount_letters(self.wage).upper()

    @api.model
    def _get_date_format(self):
        return self.env['res.function']._get_date_format_1(self.date_start).upper()