# -*- coding: utf-8 -*-


from odoo import models, fields
from odoo.addons import decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    foreign_price = fields.Float(
        'Costo extranjero',
        digits=dp.get_precision('Product Price'), groups="base.group_user",
        help="Costo utilizado para saber el costo extranjero en última compra (Importación).")
