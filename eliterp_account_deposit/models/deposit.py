# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Journal(models.Model):
    _inherit = 'account.journal'

    manage_deposits = fields.Boolean('Gestionar depósitos', default=False,
                                     help="Técnico : Identificar si diario tipo Banco se pueden realizar depósitos.")


class Payment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def cancel(self):
        if self.filtered(lambda p: p.payment_method_code == 'customer_check_printing'
                                   and p.state_check == 'deposited'):
            raise UserError(_("No se puede anular cheques recibidos en estado depositado.\n"
                              "Primero anule movimiento de depósito."))
        if self.filtered(lambda p: p.deposit):
            raise UserError(_("No se puede anular cobro con depósito validado.\n"
                              "Primero anule movimiento de depósito."))
        return super(Payment, self).cancel()

    # TODO: Será la mejor opción?
    deposit = fields.Boolean('Depositado', default=False, help="Técnico: para saber si cobro (manual) está depositado.")

class Deposit(models.Model):
    _name = "account.deposit"
    _inherit = ['mail.thread']
    _description = _("Depósito bancario")
    _order = "date desc"

    def _check_deposit(self, state='deposited'):
        """
        Colocamos estado de cheque cómo depositado
        :return:
        """
        for line in self.deposit_line_checks_collected:
            payment = line.name
            payment.update({'state_check': state})
        return True

    def _transfer_deposit(self, flag=True):
        """
        Colocamos cobro como depositado
        :return:
        """
        for line in self.deposit_line_transfer:
            payment = line.name
            payment.update({'deposit': flag})
        return True

    @api.model
    def create(self, vals):
        if 'date' in vals:
            self.env['account.fiscal.year'].valid_period(vals['date'])
        return super(Deposit, self).create(vals)

    @api.multi
    def unlink(self):
        if self.filtered(lambda d: d.state != 'draft'):
            raise UserError(_(
                    'No puedes borrar un depósito bancario con diferente de estado borrador.'))
        return super(Deposit, self).unlink()

    def _get_move_name(self):
        company = self.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code('bank.deposit')
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código 'bank.deposit' para compañía: %s") % company.name)
        return sequence

    @api.multi
    def action_post(self):
        journal = self.journal_id
        move_id = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': self.date
        })
        move_line = self.env['account.move.line'].with_context(check_move_validity=False)
        self._get_move_lines(move_line, move_id)  # Creamos líneas contables
        # Creamos línea de acreditación a la cuenta bancaria del diario
        self.env['account.move.line'].with_context(check_move_validity=True).create({
            'name': "%s: %s" % (self.journal_id.name, self.communication or '/'),
            'journal_id': journal.id,
            'account_id': self.journal_id.default_credit_account_id.id,
            'move_id': move_id.id,
            'debit': self.amount,
            'credit': 0.0,
            'date': self.date,
        })
        move_id.post()
        if self.type_deposit == 'checks_collected':
            self._check_deposit()
        if self.type_deposit == 'transfer':
            self._transfer_deposit()
        self.write({
            'state': 'posted',
            'name': self._get_move_name(),
            'move_id': move_id.id
        })
        self.move_id.write({'ref': self.name})
        return True

    @api.multi
    def action_cancel(self):
        for rec in self:
            if rec.type_deposit == 'checks_collected':
                rec._check_deposit('received')
            if rec.type_deposit == 'transfer':
                rec._transfer_deposit(False)
            rec.move_id.reverse_moves(rec.move_id.date, rec.journal_id, False)
            rec.move_id.write({'state': 'cancel'})
            rec.write({'state': 'cancel'})

    def _get_move_lines(self, move_line, move_id):
        """
        Creamos líneas de movimiento contable dependiendo del
        tipo de depósito.
        :return:
        """
        if self.type_deposit == 'cash':
            for line in self.deposit_line_cash:
                account = line.name.default_debit_account_id
                if not account:
                    raise UserError(_("Diario %s no tiene configurada cuenta de débito.") % line.name)
                move_line.create({
                    'name': line.name.name,
                    'journal_id': move_id.journal_id.id,
                    'account_id': account.id,
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                    'date': self.date,
                })
        if self.type_deposit == 'external_checks':
            for line in self.deposit_line_external_checks:
                move_line.create({
                    'name': "%s: %s" % (line.name.name, line.check_number),
                    'journal_id': move_id.journal_id.id,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                    'date': self.date,
                })
        if self.type_deposit == 'checks_collected':
            for line in self.deposit_line_checks_collected:
                move_line.create({
                    'name': "%s: %s" % (line.bank_account_id.acc_number, line.name.name),
                    'journal_id': move_id.journal_id.id,
                    'account_id': line.account_id.id,
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                    'date': self.date,
                })
        if self.type_deposit == 'transfer':
            for line in self.deposit_line_transfer:
                move_line.create({
                    'name': "Depósito desde %s" % line.name.name,
                    'journal_id': move_id.journal_id.id,
                    'account_id': self.company_id.transfer_account_id.id,
                    'move_id': move_id.id,
                    'debit': 0.0,
                    'credit': line.amount,
                    'date': self.date,
                })

    def _get_amount(self):
        """
        Monto a cargar en banco dependiendo del tipo de depósito.
        :return:
        """
        amount = 0.00
        if self.type_deposit == 'external_checks':
            for line in self.deposit_line_external_checks:
                amount += line.amount
        if self.type_deposit == 'cash':
            for line in self.deposit_line_cash:
                amount += line.amount
        if self.type_deposit == 'checks_collected':
            for line in self.deposit_line_checks_collected:
                amount += line.amount
        if self.type_deposit == 'transfer':
            for line in self.deposit_line_transfer:
                amount += line.amount
        return amount

    @api.multi
    def charge_amount(self):
        return self.update({'amount': self._get_amount()})

    @api.multi
    def charge_checks(self):
        """
        Cargamos cheques por compañía mayores a la fecha actual y
        menores a la fecha del cheque.
        :return:
        """
        self.deposit_line_checks_collected.unlink()
        today = fields.Date.today().strftime('%Y-%m-%d')
        checks = self.env['account.payment'].search([
            ('check_date', '<=', today),
            ('company_id', '=', self.company_id.id),
            ('payment_method_code', '=', 'customer_check_printing'),
            ('state_check', '=', 'received')
        ])
        lines = []
        for check in checks:
            lines.append([0, 0, {'name': check.id}])
        return self.update({'deposit_line_checks_collected': lines})

    @api.multi
    def charge_transfers(self):
        """
        Cargamos transferencias.
        :return:
        """
        self.deposit_line_transfer.unlink()
        transfers = self.env['account.payment'].search([
            ('company_id', '=', self.company_id.id),
            ('internal_movement', '=', 'transfer'),
            ('payment_method_code', '=', 'manual'),
            ('journal_id.type', '=', 'bank'),
            ('payment_type', '=', 'inbound'),
            ('state', '=', 'posted'),
            ('deposit', '=', False)
        ])
        lines = []
        for transfer in transfers:
            lines.append([0, 0, {'name': transfer.id}])
        return self.update({'deposit_line_transfer': lines})

    name = fields.Char('Referencia', index=True, copy=False, default="Nuevo")
    date = fields.Date(string='Fecha de depósito', required=True, readonly=True, default=fields.Date.context_today,
                       states={'draft': [('readonly', False)]}, track_visibility='onchange')
    amount = fields.Monetary('Monto de depósito', required=True, readonly=True, states={'draft': [('readonly', False)]})
    communication = fields.Char('Concepto', readonly=True, states={'draft': [('readonly', False)]},
                                track_visibility='onchange')
    journal_id = fields.Many2one('account.journal', string="Banco a depositar", readonly=True,
                                 states={'draft': [('readonly', False)]}, required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Validado'),
        ('cancel', 'Anulado')
    ], readonly=True, default='draft', copy=False, string="Estado", track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                  string="Moneda")
    move_id = fields.Many2one('account.move', string="Asiento contable", readonly=True)
    type_deposit = fields.Selection([
        ('cash', 'Efectivo'),
        ('external_checks', 'Cheques externos'),
        ('checks_collected', 'Cheques recaudados'),
        ('transfer', 'Transferencias (cobros)')
    ], string="Tipo de depósito", default='cash', readonly=True,
        states={'draft': [('readonly', False)]}, required=True)
    ref = fields.Char('Referencia bancaria')
    deposit_line_cash = fields.One2many('account.deposit.line.cash', 'deposit_id', readonly=True,
                                        states={'draft': [('readonly', False)]},
                                        string='Líneas de efectivo')
    deposit_line_external_checks = fields.One2many('account.deposit.line.external.checks', 'deposit_id', readonly=True,
                                                   states={'draft': [('readonly', False)]},
                                                   string='Líneas de cheques externos')
    deposit_line_checks_collected = fields.One2many('account.deposit.line.collected.check', 'deposit_id', readonly=True,
                                                    states={'draft': [('readonly', False)]},
                                                    string='Líneas de cheques recaudados')

    deposit_line_transfer = fields.One2many('account.deposit.line.transfer', 'deposit_id', readonly=True,
                                            states={'draft': [('readonly', False)]},
                                            string='Líneas de transferencias (cobros)')


class DepositLineCash(models.Model):
    _name = 'account.deposit.line.cash'
    _description = _('Linea de depósito en efectivo')

    name = fields.Many2one('account.journal', 'Efectivo', domain=[('type', '=', 'cash')], required=True)
    reference = fields.Char('Referencia')
    amount = fields.Float('Monto', required=True)
    deposit_id = fields.Many2one('account.deposit', string="Depósito", ondelete="cascade")


class DepositLineExternalChecks(models.Model):
    _name = 'account.deposit.line.external.checks'
    _description = _('Linea de depósito de cheques externos')

    name = fields.Many2one('res.bank', string='Banco', required=True)
    check_account = fields.Char('No. Cuenta', required=True)
    check_number = fields.Char('No. Cheque', required=True)
    drawer = fields.Char('Girador', required=True)
    account_id = fields.Many2one('account.account', 'Cuenta contable', required=True)
    amount = fields.Float('Monto', required=True)
    deposit_id = fields.Many2one('account.deposit', string="Depósito", ondelete="cascade")


class DepositLineCollectedcheck(models.Model):
    _name = 'account.deposit.line.collected.check'
    _description = _('Linea de depósito de cheques recaudados (cobros)')

    name = fields.Many2one('account.payment', string="Cheque", required=True)
    amount = fields.Monetary('Monto', related='name.amount', store=True, readonly=True)
    bank_account_id = fields.Many2one('res.partner.bank', related='name.partner_bank_account_id', readonly=True,
                                      string="Cuenta bancaria")
    check_date = fields.Date('Fecha de cheque', related='name.payment_date', readonly=True)
    account_id = fields.Many2one('account.account', related='name.account_inbound_id', readonly=True,
                                 string='Cuenta de cobro')
    deposit_id = fields.Many2one('account.deposit', string="Depósito", ondelete="cascade")
    currency_id = fields.Many2one('res.currency', related='name.currency_id', store=True, string="Moneda",
                                  related_sudo=False)


class DepositLineCollectedcheck(models.Model):
    _name = 'account.deposit.line.transfer'
    _description = _('Linea de depósito transferencias (cobros)')

    deposit_id = fields.Many2one('account.deposit', string="Depósito", ondelete="cascade")
    name = fields.Many2one('account.payment', string="Cobro", required=True)
    amount = fields.Monetary('Monto', related='name.amount', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='name.currency_id', store=True, string="Moneda",
                                  related_sudo=False)
