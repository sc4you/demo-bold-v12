# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class StockHelpFunctions(models.AbstractModel):
    _name = 'stock.report.help.functions'
    _description = _("Funciones de ayuda para reportes inventario")

    date = fields.Date('Inventario a fecha', default=fields.Date.context_today)
    location_ids = fields.Many2many('stock.location', string='Bodegas')
    product_ids = fields.Many2many('product.product', string='Productos')


class StockQuantPdf(models.AbstractModel):
    _name = 'report.eliterp_stock_reports.report_stock_quant'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        object_location = self.env['stock.location']
        object_product = self.env['product.product']
        if not doc['location_ids']:
            locations = object_location.search([
                ('usage', '=', 'internal')
            ])
        else:
            locations = doc['location_ids']
        if not doc['product_ids']:
            products = object_product.search([
                ('type', '=', 'product')
            ])
        else:
            products = doc['product_ids']
        data = []
        for location in locations:
            data_products = []
            for quant in location.quant_ids:
                product = quant.product_id
                if products.filtered(lambda x: x.id == product.id):
                    data_products.append({
                        'name': product.display_name,
                        'quantity': quant.quantity,
                        'qty_presentation': product._get_qty_presentation(quant.quantity),
                        'reserved_quantity': quant.reserved_quantity,
                        'available_quantity': quant.quantity - quant.reserved_quantity
                    })
            data.append({
                'location': location.display_name,
                'products': data_products
            })
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant.report',
            'docs': self.env['stock.quant.report'].browse(docids),
            'get_lines': self._get_lines,
            'data': data,
        }


class StockQuant(models.TransientModel):
    _name = 'stock.quant.report'
    _inherit = ['report.xlsx.abstract', 'stock.report.help.functions']
    _description = _("Ventana para reporte de inventario")

    def generate_xlsx_report(self, workbook, context):
        pass

    @api.multi
    def print_report_xlsx(self):
        """
        Imprimimos reporte en xlsx
        :return:
        """
        context = dict(
            date=self.date
        )
        self.write(self.create_xlsx_report('Inventario', context))
        return {
            'name': "Reporte de inventario",
            'type': 'ir.actions.act_window',
            'res_model': 'account.status.results',
            'view_mode': ' form',
            'view_type': ' form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_stock_reports.action_report_quant').report_action(self)

    audit = fields.Boolean('Auditoría', default=False,
                           help="Sirve para realizar un conteo físico del inventario, para verificar datos del sistema con lo contado.")
    qty_zero = fields.Boolean('Ocultar cantidad en cero', default=False,
                              help="Tecnico: oculta productos con disponibilidad cero.")
