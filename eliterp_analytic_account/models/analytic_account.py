# -*- coding: utf-8 -*-


from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _rec_name = 'complete_name'
    _order = 'complete_name'

    @api.depends('name', 'group_id.complete_name')
    def _compute_complete_name(self):
        for analytic in self:
            if analytic.group_id:
                analytic.complete_name = '%s / %s' % (analytic.group_id.complete_name, analytic.name)
            else:
                analytic.complete_name = analytic.name

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    complete_name = fields.Char('Nombre completo', compute='_compute_complete_name', store=True)
