# -*- coding: utf-8 -*-

from odoo import api, models


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        if not self.purchase_id:
            return {}
        if self.purchase_id.company_division_id:
            self.company_division_id = self.purchase_id.company_division_id.id
        if self.purchase_id.project_id:
            self.project_id = self.purchase_id.project_id.id
        return super(Invoice, self).purchase_order_change()
