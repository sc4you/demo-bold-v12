# -*- coding: utf-8 -*-

from odoo import api, fields, models


class Order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(Order, self)._prepare_invoice()
        invoice_vals['company_division_id'] = self.company_division_id.id
        invoice_vals['project_id'] = self.project_id.id
        return invoice_vals

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
            
    company_division_id = fields.Many2one('account.company.division', string='División',
                                          default=_default_company_division)
    project_id = fields.Many2one('account.project', string='Proyecto', track_visibility='onchange')
