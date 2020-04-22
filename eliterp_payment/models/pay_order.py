# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PayOrderAbstract(models.AbstractModel):
    _name = 'account.pay.order.abstract'
    _description = _('Lógica de las ordenes de pago')

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        """
        Verificamos el monto no sea mayor al valor por defecto
        """
        if self.amount > self.default_amount:
            raise ValidationError(
                _("Monto mayor al del saldo por pagar del documento (%.2f)." % self.default_amount))

    @api.model
    def _compute_amount(self, invoice_ids):
        total = 0
        for inv in invoice_ids:
            total += inv.residual_pay_order
        return total

    def _get_vals_document(self, active_model, active_ids):
        """
        Obtenemos los valores de la orden de pago dependiendo del documento
        Dejamos está función así para utilizar en otros modelos otros modelos
        u aplicaciones.
        :return:
        """
        vals = {}
        if active_model == 'account.invoice':
            invoice_ids = self.env['account.invoice'].browse(active_ids)
            if len(invoice_ids) > 1:
                # Revisar empresas y cuentas de facturas
                if any(invoice.state != 'open' for invoice in invoice_ids):
                    raise UserError("Soló se puede generar orden de pago de facturas por pagar.")
                if any(inv.partner_id != invoice_ids[0].partner_id for inv in invoice_ids):
                    raise UserError("Soló se puede generar orden de pago de facturas del mismo proveedor.")
                if any(inv.account_id != invoice_ids[0].account_id for inv in invoice_ids):
                    raise UserError("Soló se puede generar orden de pago de facturas con la misma cuenta por pagar.")
            vals.update({
                # Fecha del día
                'date': fields.Date.today(),
                'default_date': fields.Date.today(),
                'type': 'invoice',
                'amount': self._compute_amount(invoice_ids),
                'default_amount': self._compute_amount(invoice_ids),
                'origin': ', '.join(str(i.number) for i in invoice_ids),
                'invoice_ids': [(6, 0, invoice_ids.ids)],
                'beneficiary': invoice_ids[0].partner_id.name
            })
        return vals

    @api.model
    def default_get(self, fields):
        """
        Valores por defecto dependiendo del modelo del documento
        :param fields:
        :return:
        """
        result = super(PayOrderAbstract, self).default_get(fields)
        if 'active_ids' in self._context:
            records = self._context['active_ids']
        else:
            records = self._context['active_id']
        vals = self._get_vals_document(self._context['active_model'], records)
        result.update(vals)
        return result

    @api.multi
    @api.depends('journal_id')
    def _compute_hide_payment_method(self):
        for payment in self:
            if payment.journal_id.type not in ['bank', 'cash']:
                payment.hide_payment_method = True
                continue
            journal_payment_methods = payment.journal_id.outbound_payment_method_ids
            payment.hide_payment_method = len(journal_payment_methods) == 1 and journal_payment_methods[
                0].code == 'manual'

    @api.onchange('journal_id')
    def _onchange_journal(self):
        """
        Al cambiar la forma de pago realizamos un update de los términos de pago
        y su dominio.
        :return:
        """
        if self.journal_id:
            payment_methods = self.journal_id.outbound_payment_method_ids
            self.payment_method_id = payment_methods and payment_methods[0] or False
            return {'domain': {
                'payment_method_id': [('id', 'in', tuple(payment_methods.ids))]}}
        return {}

    date = fields.Date('Fecha de pago', default=fields.Date.context_today, required=True,
                       help="Fecha programada (futura) del pago generado.")
    type = fields.Selection([
        ('invoice', 'Facturas de proveedor')
    ], string="Tipo de origen")
    hide_payment_method = fields.Boolean(compute='_compute_hide_payment_method',
                                         string='Ocultar tipo de método de pago')
    payment_method_id = fields.Many2one('account.payment.method', string='Tipo de método de pago',
                                        help="Manual: Transferencias o pagos en efectivo.\n" \
                                             "Cheques: Se genera cheque del banco seleccionado.",
                                        required=True)
    amount = fields.Float('Monto a pagar', required=True)
    default_amount = fields.Float('Monto ficticio',
                                  help="Técnico: sirve para evitar generar una orden de "
                                       "pago con monto mayor al del documento.")
    default_date = fields.Date('Fecha ficticia', help="Técnico: sirve para evitar generar una orden de pago "
                                                      "con fecha menor a la del documento.")

    origin = fields.Char('Origen', required=True)
    beneficiary = fields.Char('Beneficiario', index=True)
    # Campos para traer los diferentes documentos para la orden de pago
    invoice_ids = fields.Many2many('account.invoice', string='Facturas')
    journal_id = fields.Many2one('account.journal', required=True, string="Forma de pago",
                                 domain=[('type', 'in', ('bank', 'cash'))])
    comment = fields.Text('Notas y comentarios')
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env.user.company_id.id)


class PayOrderWizard(models.TransientModel):
    _name = 'account.pay.order.wizard'
    _inherit = "account.pay.order.abstract"
    _description = _('Ventana para generar orden pago')


class PayOrder(models.Model):
    _name = 'account.pay.order'
    _inherit = ['mail.thread', 'account.pay.order.abstract']
    _description = _("Orden de pago")
    _order = "date desc"

    @api.multi
    def generate_payment(self):
        """
        Generamos pago desde orden de pago y llenamos con los datos de la misma
        luego redirigimos al formulario creado para su posteior validación.
        :return:
        """
        ctx = {'default_payment_type': 'outbound', 'default_partner_type': 'supplier'}
        new_payment = self.env['account.payment'].with_context(ctx)._create_new_payment(
            self)
        action = self.env.ref('eliterp_payment.action_payments_payable')
        result = action.read()[0]
        res = self.env.ref('eliterp_payment.view_form_payments_payable', False)
        result['views'] = [(res and res.id or False, 'form')]
        result['res_id'] = new_payment.id
        return result

    @api.multi
    def unlink(self):
        for pay in self:
            if pay.state != 'draft':
                raise ValidationError(_("No se puede eliminar una Orden de pago diferente de estado borrador."))
        return super(PayOrder, self).unlink()

    @api.model
    def create(self, vals):
        result = super(PayOrder, self).create(vals)
        new_name = self.env['ir.sequence'].with_context(force_company=result.company_id.id).next_by_code('pay.order')
        if not new_name:
            raise ValidationError(_("No ha creado secuencia con código 'pay.order' para %s.") % result.company_id.name)
        result.name = new_name
        return result

    name = fields.Char('Referencia de orden', index=True)
    date = fields.Date(track_visibility='onchange')
    amount = fields.Float(track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('paid', 'Pagada'),
        ('cancel', 'Anulada'),
    ], default='draft', string="Estado", readonly=True, track_visibility='onchange')
    beneficiary = fields.Char(track_visibility='onchange')
    journal_id = fields.Many2one(track_visibility='onchange')
    payment_id = fields.Many2one('account.payment', string='Pago', readonly=True)
    comment = fields.Text(track_visibility='onchange')


class Payment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    @api.returns('self')
    def _create_new_payment(self, record):
        values = {}
        values['payment_date'] = record.date
        values['payment_method_id'] = record.payment_method_id.id
        values['pay_order_id'] = record.id
        values['amount'] = record.amount
        values['journal_id'] = record.journal_id.id
        payment = self.create(values)
        payment._onchange_pay_order_id()
        return payment

    def _get_communication(self, invoices):
        """
        Concepto para facturas (Puede haber varias)
        :param invoices:
        :return:
        """
        if len(invoices) > 1:
            references = ', '.join(invoice.reference for invoice in invoices)
            communication = references
        else:
            communication = invoices[0].reference
        return communication

    @api.multi
    def data_invoice(self):
        invoice = self.pay_order_id.invoice_ids[0]
        beneficiary = invoice.partner_id.name
        partner_id = invoice.partner_id.id
        invoices = [(6, 0, self.pay_order_id.invoice_ids.ids)]
        return self.update({
            'beneficiary': beneficiary,
            'partner_id': partner_id,
            'invoice_ids': invoices,
            'communication': self._get_communication(self.pay_order_id.invoice_ids)
        })

    @api.onchange('pay_order_id')
    def _onchange_pay_order_id(self):
        if self.type_pay_order == 'invoice':
            self.data_invoice()

    @api.multi
    def post(self):
        res = super(Payment, self).post()
        for payment in self.filtered(lambda p: p.payment_type == 'outbound'):
            payment._check_pay_order_id()
            payment._update_type()
        return res

    def _update_type(self):
        """
        Creamos líneas dependiendo del tipo de origen, este método queda abierto para otras
        futuras aplicaciones.
        :param journal:
        :return:
        """
        self.pay_order_id.update({
            'payment_id': self.id,
            'state': 'paid'
        })
        return True

    def _check_pay_order_id(self):
        new_object = self.search([
            ('pay_order_id', '=', self.pay_order_id.id),
            ('state', '=', 'posted'),
            ('id', '!=', self.id)
        ])
        if new_object:
            raise ValidationError("Ya existe una Orden de pago contabilizada de la misma.")
        else:
            return

    pay_order_id = fields.Many2one('account.pay.order', string='Orden de pago', readonly=True,
                                   domain=[('state', '=', 'draft')],
                                   states={'draft': [('readonly', False)]})
    type_pay_order = fields.Selection(related='pay_order_id.type', string="Tipo de origen", store=True)
