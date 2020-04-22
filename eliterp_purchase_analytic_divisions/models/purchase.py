# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Order(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _default_company_division(self):
        company = self.env.user.company_id.id
        company_division_ids = self.env['account.company.division'].search([('company_id', '=', company)], limit=1)
        return company_division_ids

    @api.onchange('company_division_id')
    def _onchange_company_division_id(self):
        if not self.project_id:
            project_ids = self.company_division_id.project_ids
            self.project_id = project_ids and project_ids[0].id or False

    company_division_id = fields.Many2one('account.company.division', string='División', readonly=True,
                                          states={'draft': [('readonly', False)]},
                                          default=_default_company_division)
    project_id = fields.Many2one('account.project', string='Proyecto', readonly=True,
                                 states={'draft': [('readonly', False)]}, track_visibility='onchange')
