# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Line(models.Model):
    _name = 'product.line'
    _description = _('Línea de productos')

    name = fields.Char('Nombre de línea', index=True, required=True)
    categ_id = fields.Many2one('product.category', 'Categoría de producto', required=True)


class Category(models.Model):
    _inherit = 'product.category'

    line_ids = fields.One2many('product.line', 'categ_id', string='Líneas de producto')


class Presentation(models.Model):
    _name = 'product.presentation'
    _description = _('Presentación de producto')

    name = fields.Char('Nombre', index=True, required=True)
    reference = fields.Char('Referencia de presentación', size=1,
                            help="Campo qué sirve para referenciar a presentación.", required=True)

    _sql_constraints = [
        ('reference_unique', 'unique (reference)', _('La referencia de presentación debe ser única!'))
    ]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _default_presentation(self):
        presentation_ids = self.env['product.presentation'].search([], limit=1)
        return presentation_ids

    def _compute_stock_quantity_presentation(self):
        for template in self:
            if template.quantity_presentation:
                template.stock_quantity_presentation = template.qty_available // template.quantity_presentation

    lst_price = fields.Float(track_visibility="onchange")
    quantity_presentation = fields.Integer('Cantidad por presentación', default=25,
                                           help='Identifica la cantidad por unidad del tipo de presentación.')
    presentation_id = fields.Many2one('product.presentation', string='Presentación', ondelete="restrict",
                                      default=_default_presentation)
    stock_quantity_presentation = fields.Integer('Stock por presentación',
                                                 compute='_compute_stock_quantity_presentation')
    line_id = fields.Many2one('product.line', 'Línea de producto', ondelete="restrict")
    measure = fields.Char('Medida del producto',
                          help="Dimensiones del producto (altura, anchura y profundidad). Informativo para usuario.")

    _sql_constraints = [
        ('default_code_unique', 'unique (default_code)', 'La Referencia interna del producto ya está registrada!')
    ]

class Product(models.Model):
    _inherit = 'product.product'

    @api.one
    def _get_pricelist_items(self):
        """
        MM: Agregamos tipo global o por categorías.
        :return:
        """
        self.pricelist_item_ids = self.env['product.pricelist.item'].search([
            '|',
            '|',
            '|',
            ('applied_on', '=', '3_global'),
            ('categ_id', '=', self.product_tmpl_id.categ_id.id),
            ('product_id', '=', self.id),
            ('product_tmpl_id', '=', self.product_tmpl_id.id)]).ids

    @api.model
    def _get_qty_presentation(self, qty=0):
        """
        Presentacion por unidades
        :param qty:
        :return:
        """
        tmpl_id = self.product_tmpl_id
        if self.uom_id.measure_type == 'unit' and tmpl_id.quantity_presentation and tmpl_id.presentation_id:
            quantity_presentation = qty // tmpl_id.quantity_presentation
            presentation = '{0} ({1})'.format(quantity_presentation, tmpl_id.presentation_id.reference)
            unit = qty - (quantity_presentation * tmpl_id.quantity_presentation)
            return ' {0} y {1} (U)'.format(presentation, unit)
        else:
            return _('Indefinido')

    @api.depends('product_tmpl_id.quantity_presentation', 'product_tmpl_id.presentation_id')
    def _compute_stock_quantity_presentation(self):
        for product in self:
            tmpl_id = product.product_tmpl_id
            if tmpl_id.quantity_presentation > 0:
                product.stock_quantity_presentation = product.qty_available // tmpl_id.quantity_presentation

    stock_quantity_presentation = fields.Integer('Stock por presentación',
                                                 compute='_compute_stock_quantity_presentation')
