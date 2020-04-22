# -*- coding: utf-8 -*-


from odoo import models, fields


class Scrap(models.Model):
    _inherit = 'stock.scrap'

    comment = fields.Text('Notas')
