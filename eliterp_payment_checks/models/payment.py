# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.debug(_('No se puede importar librería xlsxwriter.'))


class Journal(models.Model):
    _inherit = 'account.journal'

    @api.constrains('customer_check')
    def _check_customer_check(self):
        # TODO: Pendiente, revisar qué solo sea código 'Cheques de cliente'
        if self.customer_check and len(self.inbound_payment_method_ids) > 1:
            raise ValidationError(_("Cheque de cliente soló puede tener un método de pago para cobros."))

    @api.one
    def _create_check_sequence(self):
        """
        MM: Agregamos el padding para la secuencia
        :return:
        """
        self.check_sequence_id = self.env['ir.sequence'].sudo().create({
            'name': self.name + _(": Secuencia del cheque"),
            'number_next_actual': self.start_check,
            'implementation': 'no_gap',
            'number_increment': 1,
            'company_id': self.company_id.id,
        })

    @api.one
    def update_sequence_check(self):
        self.check_sequence_id.sudo().update(
            {'number_next_actual': self.new_sequence_check}
        )
        return True

    customer_check = fields.Boolean('Gestionar cheque de cliente', default=False,
                                    help="Campo para identificar si se va a utilizar diario cómo cheque de cliente ("
                                         "pagos). Y se valide los datos.")
    start_check = fields.Integer('Inicio de secuencia de cheques', default=1, copy=False)
    current_sequence_check = fields.Integer('Cheque actual (secuencia)',
                                            related='check_sequence_id.number_next_actual',
                                            readonly=True)
    new_sequence_check = fields.Integer('Nueva secuencia (cheque)', default=1)


class AbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        ME: Aumentamos girador de cheque
        :return:
        """
        res = super(AbstractPayment, self)._onchange_partner_id()
        self.beneficiary = self.partner_id.name
        return res

    @api.depends('payment_method_code', 'internal_movement')
    def _compute_show_partner_bank(self):
        """
        ME: Para cheques de clientes
        colocamos cuenta bancaria de cliente.
        :return:
        """
        result = super(AbstractPayment, self)._compute_show_partner_bank()
        if self.payment_method_code == 'customer_check_printing':
            self.show_partner_bank_account = True
        return result


class Payment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def print_check_xlsx(self):
        """
        Imprimimos cheque en xlsx
        :return:
        """
        self.write(self.create_xlsx_report('Cheque', None))

    def create_xlsx_report(self, name, context=None):
        name = name + '.xlsx'
        workbook = xlsxwriter.Workbook(name, self.get_workbook_options())
        self.generate_xlsx_report(workbook, context)
        workbook.close()
        with open(name, "rb") as file:
            file = base64.b64encode(file.read())
        data = {
            'file': file,
            'file_name': name
        }
        return data

    def get_workbook_options(self):
        return {'in_memory': True}

    def generate_xlsx_report(self, workbook, context):
        # TODO: Revisar está función
        pass

    def generate_xlsx_report(self, workbook, context):
        # Formatos
        money_format = workbook.add_format({'num_format': '$#,##0.00', 'bold': 1})
        bold = workbook.add_format({'bold': 1})
        sheet = workbook.add_worksheet('Cheque')
        amount_words = self.env['res.function'].get_amount_to_word(self.amount).upper()
        bic = self.journal_id.bank_id.bic  # Me sirve para referencia el banco del cheque
        date = self.check_date.strftime('%Y/%m/%d')
        if bic == '13':
            # Pichincha
            sheet.set_margins(left=0.18, right=0.7, top=0.0, bottom=0.75)
            # Columnas
            sheet.set_column("A:A", 7.29)
            sheet.set_column("B:B", 10.71)
            sheet.set_column("C:C", 10.71)
            sheet.set_column("D:D", 10.71)
            sheet.set_column("F:F", 12.8)
            sheet.set_column("E:E", 13.14)
            # Filas
            sheet.set_default_row(15)
            sheet.set_row(0, 10.50)
            sheet.set_row(3, 19.50)
            sheet.set_row(4, 10.50)
            sheet.set_row(5, 13.50)
            sheet.set_row(7, 18)
            # Datos
            sheet.write(3, 1, self.beneficiary, bold)
            sheet.write(3, 5, self.amount, money_format)
            sheet.write(5, 1, amount_words, bold)
            sheet.write(7, 0, 'GUAYAQUIL, %s' % date, bold)
        elif bic == '100':
            # Internacional
            sheet.set_margins(left=0.04, right=0.7, top=0.0, bottom=0.75)
            # Columnas
            sheet.set_column("A:A", 8.14)
            sheet.set_column("B:B", 10.71)
            sheet.set_column("C:C", 10.71)
            sheet.set_column("D:D", 10.71)
            sheet.set_column("E:E", 10.71)
            sheet.set_column("F:F", 0.33)
            sheet.set_column("G:G", 11.57)
            # Filas
            sheet.set_default_row(15)
            sheet.set_row(0, 8.25)
            sheet.set_row(1, 18)
            sheet.set_row(2, 18)
            sheet.set_row(3, 8.25)
            sheet.set_row(7, 6)
            sheet.set_row(8, 13.50)
            # Datos
            sheet.write(4, 1, self.beneficiary, bold)
            sheet.write(4, 6, self.amount, money_format)
            sheet.write(5, 1, amount_words, bold)
            sheet.write(8, 0, 'GUAYAQUIL, %s' % date, bold)
        elif bic == 'XXX':
            # Margins
            sheet.set_margins(left=0.0, right=0.0, top=0.0, bottom=0.0)
            # Columnas
            sheet.set_column("A:A", 1.86)
            sheet.set_column("B:B", 8.64)
            sheet.set_column("C:C", 10.71)
            sheet.set_column("D:D", 10.71)
            sheet.set_column("E:E", 10.71)
            sheet.set_column("F:F", 12.43)
            sheet.set_column("G:G", 11.57)
            # Filas
            sheet.set_default_row(15)
            sheet.set_row(0, 10.50)
            sheet.set_row(3, 20.25)
            sheet.set_row(4, 6)
            sheet.set_row(5, 13.50)
            sheet.set_row(7, 18)
            # Datos
            sheet.write(3, 2, self.beneficiary, bold)
            sheet.write(3, 6, self.amount, money_format)
            sheet.write(5, 2, amount_words, bold)
            sheet.write(7, 1, 'GUAYAQUIL, %s' % date, bold)
        elif bic == 'XX':
            # Margins
            sheet.set_margins(left=0.18, right=0.7, top=0.0, bottom=0.75)
            # Columnas
            sheet.set_column("A:A", 7.29)
            sheet.set_column("B:B", 10.71)
            sheet.set_column("C:C", 10.71)
            sheet.set_column("D:D", 10.71)
            sheet.set_column("F:F", 12.86)
            sheet.set_column("E:E", 13.14)
            # Filas
            sheet.set_default_row(15)
            sheet.set_row(0, 12)
            sheet.set_row(3, 19.50)
            sheet.set_row(4, 3.75)
            sheet.set_row(5, 16.50)
            sheet.set_row(6, 19.50)
            sheet.set_row(7, 18.00)
            # Datos
            sheet.write(3, 1, self.beneficiary, bold)
            sheet.write(3, 5, self.amount, bold)
            sheet.write(5, 1, amount_words, bold)
            sheet.write(7, 0, 'GUAYAQUIL, %s' % date, bold)
        else:
            return

    @api.multi
    def cancel(self):
        res = super(Payment, self).cancel()
        for rec in self.filtered(lambda p: p.payment_method_code in ['check_printing', 'customer_check_printing']):
            rec.state_check = 'cancel'
        return res

    @api.multi
    @api.returns('self')
    def _create_new_payment(self, record):
        """
        ME: Si es método de pago cheque, mostramos el cheque por defecto.
        :param record:
        :return: self
        """
        payment = super(Payment, self)._create_new_payment(record)
        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        if payment.payment_method_id == payment_method_check:
            payment.check_number = payment.journal_id.check_next_number
        return payment

    @api.one
    @api.depends('check_date', 'payment_date')
    def _compute_check_type(self):
        """
        Calculamos si cheque es a la fecha o corriente
        :return:
        """
        if self.check_date > self.payment_date:
            self.check_type = 'to_date'
        else:
            self.check_type = 'current'

    @api.constrains('check_number')
    def _check_payment_check_number(self):
        self.ensure_one()
        if self.check_number <= 0 and self.payment_method_code in ['check_printing', 'customer_check_printing']:
            raise ValidationError(_("# de cheque no puede ser menor a 1."))
        if self.search([('check_number', '=', self.check_number), ('journal_id', '=', self.journal_id.id),
                        ('payment_method_code', '=', 'check_printing'), ('id', '!=', self.id)]):
            raise ValidationError(_("Ya existe cheque %s emitido para cuenta bancaria %s.\n"
                                    "Cambie la secuencia en el Diario del mismo.") % (
                                  self.check_number, self.journal_id.name))

    @api.onchange('amount', 'currency_id')
    def _onchange_amount(self):
        """
        MM
        :return:
        """
        return

    @api.depends('payment_type', 'payment_method_code')
    def _compute_account_inbound_id(self):
        for record in self:
            if record.payment_type != 'inbound' or record.payment_method_code != 'customer_check_printing':
                continue
            else:
                account = record.journal_id.default_debit_account_id
                record.account_inbound_id = account.id

    @api.depends('amount', 'payment_method_code')
    def _compute_amount_in_words(self):
        """
        Calculamos el monto en letras del cheque
        :return:
        """
        for payment in self:
            function = self.env['res.function']
            if payment.payment_method_code not in ['check_printing', 'customer_check_printing']:
                continue
            text = function._get_amount_letters(payment.amount)
            payment.check_amount_in_words = text.upper()

    @api.multi
    def post(self):
        """
        MM: Cambiamos la secuencia del cheque
        y la ref del asiento contable aumentamos dato del cheque
        :return:
        """
        res = super(Payment, self).post()

        for pc in self.filtered(lambda x: x.payment_method_code in ['check_printing', 'customer_check_printing']):
            move = pc.move_line_ids.mapped('move_id')
            move.ref = move.ref + _(": Cheque # ") + str(pc.check_number)

        payment_method_check = self.env.ref('account_check_printing.account_payment_method_check')
        for payment in self.filtered(
                lambda p: p.payment_method_id == payment_method_check and not p.check_manual_sequencing):
            sequence = payment.journal_id.check_sequence_id
            payment.check_number = sequence.next_by_id()
        return res

    @api.model
    def _default_state(self):
        if self._context.get('default_payment_type', False):
            if self._context.get('default_payment_type') == 'outbound':
                return 'issued'
            else:
                return 'received'
        else:
            return 'received'

    check_amount_in_words = fields.Char(string="Monto en letras", compute='_compute_amount_in_words')  # CM
    check_number = fields.Integer(track_visibility='onchange')
    check_date = fields.Date("Fecha de cheque", readonly=True, states={'draft': [('readonly', False)]},
                             default=fields.Date.context_today)
    account_inbound_id = fields.Many2one('account.account', string='Cuenta de cobro',
                                         compute='_compute_account_inbound_id', store=True)
    check_type = fields.Selection([('current', 'Corriente'), ('to_date', 'A la fecha')], string='Tipo de cheque'
                                  , compute='_compute_check_type', store=True)
    # TODO: Conciliado colocar a nivel de Conciliación
    state_check = fields.Selection([
        ('received', 'Recibido'),
        ('deposited', 'Depositado'),
        ('issued', 'Emitido'),
        ('charged', 'Debitado'),
        ('reconciled', 'Conciliado'),
        ('cancel', 'Anulado')
    ], string='Estado de cheque', track_visibility='onchange', default=_default_state)
    file = fields.Binary('Cheque (.xlsx)')
    file_name = fields.Char('Nombre de cheque', readonly=True)
