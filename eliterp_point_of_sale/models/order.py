# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Order(models.Model):
    _inherit = 'pos.order'

    amount_untaxed = fields.Float(string='Subtotal', digits=0, readonly=True, required=True)

    @api.model
    def _order_fields(self, ui_order):
        """
        ME: Añadimos el campo subtotal
        :param ui_order:
        :return:
        """
        order_fields = super(Order, self)._order_fields(ui_order)
        order_fields['amount_untaxed'] = ui_order.get('amount_untaxed', 0)
        return order_fields

    @api.onchange('statement_ids', 'lines', 'lines')
    def _onchange_amount_all(self):
        """
        MR: Aumentamos campo subtotal para mostrar en GUI de POS
        :return:
        """
        for order in self:
            currency = order.pricelist_id.currency_id
            order.amount_paid = sum(payment.amount for payment in order.statement_ids)
            order.amount_return = sum(payment.amount < 0 and payment.amount or 0 for payment in order.statement_ids)
            order.amount_tax = currency.round(
                sum(self._amount_line_tax(line, order.fiscal_position_id) for line in order.lines))
            amount_untaxed = currency.round(sum(line.price_subtotal for line in order.lines))
            order.amount_untaxed = amount_untaxed
            order.amount_total = order.amount_tax + amount_untaxed

    def _prepare_invoice(self):
        """
        ME: Aumentamos los datos de facturación electrónica
        :return:
        """
        invoice_vals = super(Order, self)._prepare_invoice()

        # Borramos datos innecesarios (reference es computado)
        del (invoice_vals['reference'])
        del (invoice_vals['name'])

        # Nuevos datos
        point_printing = self.config_id.point_printing_id
        invoice_vals['point_printing_id'] = point_printing.id
        invoice_vals['billing_adress'] = self.partner_id.street
        invoice_vals['authorized_voucher_id'] = self.env['sri.authorized.vouchers'].search([('code', '=', '18')])[0].id
        invoice_number = point_printing._get_electronic_sequence()
        invoice_vals['invoice_number'] = invoice_number.zfill(9)
        return invoice_vals

    @api.multi
    def action_pos_order_invoice(self):
        """
        ME: Actualizamos líneas de pagos con datos
        de la factura luego de crearla.
        :return object:
        """
        self.ensure_one()
        result = super(Order, self).action_pos_order_invoice()
        invoice = self.env['account.invoice'].browse(result['res_id'])
        for line in self.statement_ids:
            line.update({
                'name': invoice.reference  # name (pos.order)
            })
        return result
