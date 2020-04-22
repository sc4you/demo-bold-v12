# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class BankNote(models.Model):
    _name = 'account.bank.note'
    _inherit = ['mail.thread']
    _description = _("Nota bancaria")
    _order = "note_date desc"

    @api.model
    def create(self, vals):
        if 'note_date' in vals:
            self.env['account.fiscal.year'].valid_period(vals['note_date'])
        res = super(BankNote, self).create(vals)
        return res

    def _create_account_move_line(self, name, debit, credit, account, check_move, journal, move, note_date):
        """
        Creamos una línea de movimiento contable dependiendo del tipo de nota bancaria
        :param name:
        :param debit:
        :param credit:
        :param account:
        :param check_move:
        :param journal:
        :param move:
        :param note_date:
        :return: object
        """
        self.env['account.move.line'].with_context(check_move_validity=check_move).create({
            'name': "%s: %s" % (journal.name, name),
            'journal_id': journal.id,
            'account_id': account.id,
            'move_id': move,
            'debit': debit,
            'credit': credit,
            'date': note_date
        })

    @api.multi
    def action_button_print(self):
        """
        Imprimimos nota bancaria
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_account_bank_note.action_report_bank_note').report_action(self)

    def _get_name(self, code):
        company = self.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code(code)
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código '%s' para compañía: %s") % (code, company.name))
        return sequence

    @api.multi
    def action_button_posted(self):
        """
        Contabilizamos la nota bancaria dependiendo del tipo
        le creamos el nombre.
        """
        self.ensure_one()
        journal = self.journal_id
        name = self._get_name('bank.debit.note') if self.type == 'debit' else self._get_name('bank.credit.note')
        move_id = self.env['account.move'].create({
            'journal_id': journal.id,
            'ref': name,
            'date': self.note_date,
        })
        if self.type == "debit":
            self._create_account_move_line(self.concept, 0.00, self.amount, journal.default_credit_account_id,
                                           False,
                                           journal, move_id.id, self.note_date)
            self._create_account_move_line(self.account_id.name, self.amount, 0.00, self.account_id, True, journal,
                                           move_id.id,
                                           self.note_date)
        if self.type == "credit":
            self._create_account_move_line(self.account_id.name, 0.00, self.amount, self.account_id, False, journal,
                                           move_id.id,
                                           self.note_date)
            self._create_account_move_line(self.concept, self.amount, 0.00, journal.default_debit_account_id,
                                           True,
                                           journal, move_id.id, self.note_date)
        move_id.post()
        return self.write({
            'state': 'posted',
            'name': name,
            'move_id': move_id.id
        })

    @api.constrains('amount')
    def _check_amount(self):
        if not self.amount > 0:
            raise ValidationError(_("La nota bancaria debe tener un monto mayor a 0."))

    @api.multi
    def unlink(self):
        for record in self:
            if record.move_id:
                raise UserError(_(
                    'No puedes borrar una nota bancaria con asiento contable.'))
        return super(BankNote, self).unlink()

    name = fields.Char('Referencia', copy=False, index=True)
    concept = fields.Char('Concepto', required=True, readonly=True,
                          states={'draft': [('readonly', False)]}, track_visibility='onchange')
    note_date = fields.Date('Fecha de nota bancaria', default=fields.Date.context_today, required=True, readonly=True,
                            states={'draft': [('readonly', False)]})
    amount = fields.Monetary('Monto', required=True, readonly=True,
                             states={'draft': [('readonly', False)]})
    account_id = fields.Many2one('account.account', 'Cuenta contable',
                                 required=True, readonly=True,
                                 states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Banco', required=True,
                                 readonly=True,
                                 states={'draft': [('readonly', False)]})
    move_id = fields.Many2one('account.move', string='Asiento contable', copy=False, readonly=True)
    type = fields.Selection([('credit', 'Crédito'), ('debit', 'Débito')], string='Tipo de nota bancaria',
                            track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('posted', 'Contabilizado'),
        ('cancel', 'Anulado')
    ], readonly=True, default='draft', copy=False, string="Estado", track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id,
                                  string="Moneda")
