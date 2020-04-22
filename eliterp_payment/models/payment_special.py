# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PaymentSpecialInvoice(models.Model):
    _name = 'account.payment.special.invoice'
    _order = 'residual asc'
    _description = _("Línea de factura en cobro espscial")

    @api.multi
    def action_view_refund(self):
        self.ensure_one()
        result = self.invoice_id.action_view_refund()
        result['target'] = 'new'
        return result

    @api.multi
    def action_view_retention(self):
        self.ensure_one()
        result = self.invoice_id.action_view_retention()
        result['target'] = 'new'
        return result

    invoice_id = fields.Many2one('account.invoice', 'Factura')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, string="Moneda",
                                  related_sudo=False)
    name = fields.Char('No. Factura', related="invoice_id.reference")
    date_due = fields.Date('Fecha vencimiento', related='invoice_id.date_due', store=True)
    have_refund = fields.Boolean(related='invoice_id.have_refund', string='Tiene nota de crédito')
    retention_id = fields.Many2one('account.retention', related='invoice_id.retention_id', string='Retención')
    amount_total = fields.Monetary('Monto de factura', related='invoice_id.amount_total', store=True)
    residual = fields.Monetary('Monto adeudado', related='invoice_id.residual', store=True)
    amount_payable = fields.Float('Monto a cobrar')
    payment_special_id = fields.Many2one('account.payment.special', string='Cobro especial', ondelete="cascade")


class Payment(models.Model):
    _inherit = "account.payment"

    payment_special_id = fields.Many2one('account.payment.special', 'Cobro especial', ondelete="cascade")


class PaymentSpecial(models.Model):
    _name = "account.payment.special"
    _inherit = ['mail.thread']
    _description = _("Cobros especiales")
    _order = "date desc"

    @api.multi
    def unlink(self):
        """
        Verificamos al borrar
        :return:
        """
        for ps in self:
            if ps.state != 'draft':
                raise UserError("No se puede eliminar un pago especial qué no este en estado borrador.")
        return super(PaymentSpecial, self).unlink()


    @api.multi
    def action_button_cancel(self):
        for rec in self:
            for payment in rec.payment_ids:
                payment.cancel()
            rec.state = 'cancel'

    @api.one
    def _check_lines(self):
        amount_payable = sum(i.amount_payable for i in self.invoice_ids)
        if self.amount_payments != amount_payable:
            raise ValidationError(_("Monto a pagar diferente al total de cobros.\n"
                                    "Debería crear línes de cobros y dar clic en el botón 'Cargar en facturas'."))

    @api.one
    def _reconcile_invoices(self, move):
        line_move_payment = move.line_ids.filtered(
            lambda x: x.account_id == self.customer_id.property_account_receivable_id)
        for invoice in sorted(self.invoice_ids, key=lambda p: p.amount_payable):
            line_move_invoice = invoice.invoice_id.move_id.line_ids.filtered(
                lambda x: x.account_id == self.customer_id.property_account_receivable_id)
            (line_move_payment + line_move_invoice).reconcile()
        return True

    @api.multi
    def action_button_cancel(self):
        for rec in self:
            for payment in rec.payment_ids:
                payment.cancel()
            rec.state = 'cancel'

    @api.multi
    def action_button_validate(self):
        for rec in self:
            rec._check_lines()
            for payment in sorted(rec.payment_ids, key=lambda p: p.amount, reverse=True):
                payment.post()
                move = payment.move_line_ids.mapped('move_id')
                rec._reconcile_invoices(move)
                payment.move_id = move.id
            rec.state = 'posted'

    def _set_payments(self, invoices, total):
        for invoice in invoices:
            if total == 0.00:
                continue
            if invoice.residual <= total:
                invoice.update({
                    'amount_payable': invoice.residual
                })
                total = total - invoice.residual
            else:
                invoice.update({
                    'amount_payable': total
                })
                total = 0.00
        return True

    @api.one
    @api.depends('payment_ids.amount')
    def _compute_total_payments(self):
        """
        Calculamos el total de líneas de cobro
        :return:
        """
        self.amount_payments = sum(line.amount for line in self.payment_ids)

    @api.one
    @api.depends('invoice_ids')
    def _compute_total_invoices(self):
        """
        Calculamos el total de facturas de cliente
        :return:
        """
        self.amount_invoices = sum(line.residual for line in self.invoice_ids)

    @api.multi
    def charge_invoices(self):
        """
        Cargamos las facturas de ventas del cliente
        :return:
        """
        self.invoice_ids.unlink()
        invoices = self.env['account.invoice'].search([
            ('partner_id', '=', self.customer_id.id),
            ('state', '=', 'open')
        ])
        list_invoices = []
        for invoice in invoices:
            list_invoices.append([0, 0, {
                'invoice_id': invoice.id
            }])
        return self.update({'invoice_ids': list_invoices})

    @api.multi
    def charge_payments(self):
        """
        Cargamos pagos a líneas de facturas
        :return:
        """
        self.ensure_one()
        if not self.payment_ids:
            raise UserError(_("No tiene líneas de cobros creadas."))
        self._set_payments(self.invoice_ids, self.amount_payments)

    name = fields.Char('Referencia de cobro', required=True, index=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    date = fields.Date('Fecha de emisión', default=fields.Date.context_today, required=True,
                       readonly=True, states={'draft': [('readonly', False)]})
    customer_id = fields.Many2one('res.partner', required=True, string='Cliente', track_visibility='onchange',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    invoice_ids = fields.One2many('account.payment.special.invoice',
                                  'payment_special_id',
                                  string='Líneas de facturas',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    payment_ids = fields.One2many('account.payment',
                                  'payment_special_id',
                                  string='Líneas de cobro',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    amount_payments = fields.Monetary('Total de cobros', compute='_compute_total_payments',
                                      track_visibility='onchange')
    amount_invoices = fields.Monetary('Total de facturas', compute='_compute_total_invoices')
    state = fields.Selection([('draft', 'Borrador'), ('posted', 'Validada'), ('cancel', 'Anulada')], string="Estado",
                             default='draft', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                  string="Moneda")
