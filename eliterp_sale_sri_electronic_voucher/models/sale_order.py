# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class Warehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_set_picking_done = fields.Boolean(string="Validar entregas",
                                         help="Técnico: validamos entregas en pedido automáticamente al crear factura.")


class Order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super(Order, self)._prepare_invoice()
        invoice_number = self.point_printing_id._get_electronic_sequence()
        invoice_vals['invoice_number'] = invoice_number
        return invoice_vals

    @api.multi
    def set_done_pickings(self):
        self.ensure_one()
        imediate_object = self.env['stock.immediate.transfer']
        warehouse = self.warehouse_id
        if warehouse.is_set_picking_done and self.picking_ids:
            for picking in self.picking_ids:
                if picking.state in ['done', 'cancel']:
                    continue
                picking.action_confirm()
                picking.action_assign()
                imediate_record = imediate_object.create({'pick_ids': [(4, self.picking_ids.id)]})
                imediate_record.process()
        self._cr.commit()
        return True

    @api.multi
    def make_electronic_invoice(self):
        """
        Generamos factura electrónica y si edificio
        tienen configurado picking automático lo hacemos.
        :return:
        """
        self.ensure_one()
        if self.state != 'sale':
            raise ValidationError(_("Notas de pedido deben estar en estado 'nota de pedido'."))

        # Validar pickings
        self.set_done_pickings()

        # Listado de IDS de facturas creadas
        invoices = self.action_invoice_create()

        # Validamos cada factura, primero hacemos el método onchange de
        # invoice_number para cálculo de campo reference
        object_invoice = self.env['account.invoice']
        for id_invoice in invoices:
            invoice = object_invoice.browse(id_invoice)
            invoice._onchange_invoice_number()
            invoice.action_invoice_open()
