# -*- coding: utf-8 -*-


from odoo import models, fields, api


class Quant(models.Model):
    _inherit = 'stock.quant'

    @api.depends('product_id', 'quantity')
    def _compute_qty_presentation(self):
        """
        Filtramos solo las mayores a 0 y mostramos
        su presentación.
        :return:
        """
        for sq in self.filtered(lambda a: a.quantity > 0):
            sq.qty_presentation = sq.product_id._get_qty_presentation(sq.quantity)

    qty_presentation = fields.Char('DpP' , compute='_compute_qty_presentation')
    area_id = fields.Many2one('stock.location.area.line', string="Área")
