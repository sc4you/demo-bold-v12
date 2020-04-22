# -*- coding: utf-8 -*-


from odoo import fields, models, api, _
from datetime import date
from odoo.exceptions import ValidationError, UserError


class PaymentLine(models.Model):
    _name = 'account.payment.line'
    _description = _("Línea de cuenta contable")
    _rec_name = 'account_id'
    _order = "amount desc"

    partner_id = fields.Many2one('res.partner', string="Empresa")
    account_id = fields.Many2one('account.account', required=True, string="Cuenta contable")
    amount = fields.Float('Monto', required=True)
    payment_id = fields.Many2one('account.payment', string='Pago', ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Compañía',
                                 related='payment_id.company_id', store=True, readonly=True, related_sudo=False)


class AbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    @api.depends('journal_id', 'amount', 'amount_delivered', 'currency_id')
    def _compute_amount_return(self):
        for pay in self.filtered(lambda p: p.payment_type == 'inbound' and p.journal_id.type == 'cash'):
            amount = pay.amount_delivered - pay.amount
            pay.amount_return = amount if amount > 0 else 0

    @api.depends('payment_method_code', 'internal_movement')
    def _compute_show_partner_bank(self):
        """
        MM: Soló mostramos para pagos de clientes es banco
        :return:
        """
        for payment in self:
            if payment.payment_type != 'inbound' or payment.internal_movement != 'transfer':
                payment.show_partner_bank_account = False
            else:
                payment.show_partner_bank_account = bool(payment.journal_id.type == 'bank')

    @api.depends('journal_id', 'payment_type')
    def _compute_validate_internal_movement(self):
        for payment in self:
            if payment.payment_type == 'inbound' and payment.journal_id.type == 'bank' and payment.payment_method_code == 'manual':
                payment.validate_internal_movement = True

    @api.depends('journal_id', 'payment_type')
    def _compute_show_cash(self):
        for pay in self.filtered(lambda p: p.payment_type == 'inbound' and p.journal_id.type == 'cash'):
            pay.show_cash = True

    show_cash = fields.Boolean('Mostrar transacciones efectivo', compute='_compute_show_cash')
    amount_delivered = fields.Monetary(string='Cantidad entregada')
    amount_return = fields.Monetary("Cambio a entregar", compute='_compute_amount_return', readonly=True)
    internal_movement = fields.Selection([('transfer', 'Transferencia'), ('deposit', 'Depósito')],
                                         string="Movimiento")
    movement_reference = fields.Char('Referencia', help="Colocar referencia de transferencia/depósito")
    validate_internal_movement = fields.Boolean('Validar tipo de movimiento',
                                                compute='_compute_validate_internal_movement')


class Payment(models.Model):
    _inherit = "account.payment"

    def _get_liquidity_move_line_vals(self, amount):
        """
        Cuando es transferencia y pago de cliente
        :return:
        """
        vals = super(Payment, self)._get_liquidity_move_line_vals(amount)
        if self.internal_movement and self.payment_type == 'inbound' and self.payment_method_code == 'manual':
            vals.update({'account_id': self.company_id.transfer_account_id.id})
        return vals

    @api.multi
    def cancel(self):
        """
        MM: No borramos asiento contable lo reversamos
        # TODO: Colocar descripción de ventana emergente
        :return:
        """
        for rec in self:
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.reverse_moves(move.date, move.journal_id, False)
                move.write({'state': 'cancel'})
            # Si tiene orden de pago la cancelamos
            if rec.pay_order_id:
                rec.pay_order_id.write({'state': 'cancel'})
            rec.state = 'cancelled'

    @api.model
    def create(self, vals):
        """
        MM: Creamos nuevo registro y validamos período contable
        :param vals:
        :return: object
        """
        if 'date_payment' in vals:
            self.env['account.fiscal.year'].valid_period(vals['date_payment'])
        res = super(Payment, self).create(vals)
        return res

    def _get_name(self, code):
        """
        Secuencia del movimiento
        :param code:
        :return:
        """
        company = self.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code(code)
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código '%s' para compañía: %s") % (code, company.name))
        return sequence

    def _get_move_name(self, payment_type):
        """
        Nombre del movimiento
        :param payment_type:
        :return:
        """
        if payment_type == 'inbound':
            code = "payment.inbound"
        elif payment_type == 'outbound':
            code = "payment.outbound"
        else:
            code = "wire.transfer"
        return self._get_name(code)

    def _get_move_lines_not_invoice(self, move_id):
        number_accounts = len(self.account_ids)
        for line in self.account_ids:
            number_accounts -= 1
            if number_accounts == 0:
                self.env['account.move.line'].with_context(check_move_validity=True).create({
                    'name': line.account_id.name,
                    'journal_id': move_id.journal_id.id,
                    'partner_id': line.partner_id.id or self.partner_id.id or False,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'credit': 0.0,
                    'debit': line.amount,
                    'date': self.payment_date,
                })
            else:
                self.env['account.move.line'].with_context(check_move_validity=False).create({
                    'name': line.account_id.name,
                    'journal_id': move_id.journal_id.id,
                    'partner_id': line.partner_id.id or self.partner_id.id or False,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'credit': 0.0,
                    'debit': line.amount,
                    'date': self.payment_date
                })

    def _get_payment_cashier(self):
        """
        Obtenemos cajero si usuario fue asignado
        a una caja registradora.
        :return:
        """
        cashier_id = False
        payment_cashier = self.env['account.payment.cashier']
        for cashier in payment_cashier.sudo().search([]):
            users = cashier.mapped('user_ids')
            if self.env.user.id in users.ids:
                cashier_id = cashier.id
                break
        return cashier_id

    @api.multi
    def post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Solo se puede contabilizar un pago en estado borrador."))

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(
                    _("El pago no puede ser procesado porque las facturas no está en estado por pagar!"))

            if not rec.name:
                rec.name = self._get_move_name(rec.payment_type)

            # Para pagos generales, TODO: Ver si es la mejor forma de hacerlo
            # Revisar error en Monedas
            if rec.payment_type == 'outbound' and rec.type_pay_order != 'invoice':
                move = self.env['account.move'].create(self._get_move_vals())
                from_payment = self._get_shared_move_line_vals(0.00, self.amount, False, move.id, False)
                from_payment.update({
                    'account_id': rec.journal_id.default_debit_account_id.id
                })
                move_line_payment = self.env['account.move.line'].with_context(check_move_validity=False)
                move_line_payment.create(from_payment)
                self._get_move_lines_not_invoice(move)
                move.post()
                rec.write({'state': 'posted', 'move_id': move.id, 'move_name': move.name})
                return True

            # TODO: Ver si es mejor forma
            payment_cashier_id = False
            if rec.payment_type == 'inbound':
                payment_cashier_id = rec._get_payment_cashier()

            # Creamos asiento contable
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)

            # Transferencias de diarios
            if rec.payment_type == 'transfer':
                transfer_credit_aml = move.line_ids.filtered(
                    lambda r: r.account_id == rec.company_id.transfer_account_id)
                transfer_debit_aml = rec._create_transfer_entry(amount)
                (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.write({
                'state': 'posted',
                'move_name': move.name,
                'payment_cashier_id': payment_cashier_id
            })
        return True

    @api.model
    def _get_report_filename(self):
        if self.payment_type == 'inbound':
            return 'Pago %s' % self.name
        elif self.payment_type == 'outbound':
            return 'Cobro %s' % self.name
        else:
            return 'Transferencia %s' % self.name

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            if data.pay_order_id:
                res.append((data.id, "%s [%s]" % (data.name, data.pay_order_id.name)))
            else:
                res.append((data.id, "%s" % data.name or '*'))
        return res

    @api.multi
    def action_print_payment(self):
        self.ensure_one()
        return self.env.ref('eliterp_payment.action_report_payment').report_action(self)

    journal_id = fields.Many2one(track_visibility='onchange')
    payment_date = fields.Date(track_visibility='onchange')
    move_id = fields.Many2one('account.move', string="Asiento contable", readonly=True)
    movement_reference = fields.Char('Referencia', help="Colocar referencia de transferencia/depósito")
    internal_movement = fields.Selection([('transfer', 'Transferencia'), ('deposit', 'Depósito')],
                                         string="Movimiento",
                                         readonly=True,
                                         states={'draft': [('readonly', False)]})
    account_ids = fields.One2many('account.payment.line', 'payment_id', string='Líneas de cuentas contables',
                                  readonly=True,
                                  states={'draft': [('readonly', False)]})
    beneficiary = fields.Char('Beneficiario', readonly=True, states={'draft': [('readonly', False)]},
                              track_visibility='onchange')
    transfer_code = fields.Char('Código de transferencia')
    ref_transfer = fields.Char('Referencia')

    _sql_constraints = [
        ('transfer_unique', 'unique (journal_id, transfer_code, state)',
         'El código de transferencia debe ser único por cuenta bancaria.')
    ]
