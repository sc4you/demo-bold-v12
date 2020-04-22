# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',  # Customer Invoice
    'out_invoice': 'out_refund',  # Customer Invoice
    'in_invoice': 'in_refund',  # Vendor Bill
    'out_refund': 'out_invoice',  # Customer Credit Note
    'in_refund': 'in_invoice',  # Vendor Credit Note
}

TYPEVOUCHER = {
    'out_invoice': 'customer',
    'in_invoice': 'supplier',
}


class AccountInvoiceTax(models.Model):
    _inherit = 'account.invoice.tax'

    @api.model
    def create(self, values):
        """
        Si es nota de crédito se cambia impuestos a no manual
        :param values:
        :return:
        """
        if 'refund' in self._context:
            values.update({'manual': False})
        return super(AccountInvoiceTax, self).create(values)


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        """
        Al validar NC la consolidamos con origen de factura
        :return:
        """
        res = super(Invoice, self).action_invoice_open()
        if self.type in ['in_refund', 'out_refund']:
            self._reconcile_invoice_refund(self.move_id)
        return res

    @api.multi
    def _reconcile_invoice_refund(self, move):
        """
        Consolidamos pagos de facturas con notas de crédito
        :return:
        """
        self.ensure_one()
        movelines = self.refund_invoice_id.move_id.line_ids
        to_reconcile_ids = {}
        to_reconcile_lines = self.env['account.move.line']
        for line in movelines:
            if line.account_id.id == self.account_id.id:
                to_reconcile_lines += line
                to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
            if line.reconciled:
                line.sudo().remove_move_reconcile()
        for tmpline in move.line_ids:
            if tmpline.account_id.id == self.account_id.id:
                to_reconcile_lines += tmpline
        to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()

    @api.multi
    def _compute_have_refund(self):
        """
        Vemos si tiene por lo menos una nota de crédito mostramos botón.
        :return:
        """
        for invoice in self:
            refunds = self.search([('refund_invoice_id', '=', invoice.id)])
            invoice.have_refund = True if refunds else False

    def action_view_refund(self):
        """
        Acción para ver las notas de crédito asociadas a la factura
        :return:
        """
        refunds = self.search([('refund_invoice_id', '=', self.id)])
        imd = self.env['ir.model.data']
        if self.type == 'in_invoice':
            action = imd.xmlid_to_object('account.action_invoice_in_refund')
            list_view_id = imd.xmlid_to_res_id('account.invoice_supplier_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        else:
            action = imd.xmlid_to_object('account.action_invoice_in_refund')
            list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
            form_view_id = imd.xmlid_to_res_id('account.invoice_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(refunds) > 1:
            result['domain'] = "[('id','in',%s)]" % refunds.ids
        elif len(refunds) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = refunds.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """ MM: Prepare the dict of values to create the new credit note from the invoice.
            This method may be overridden to implement custom
            credit note generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice as credit note
            :param string date_invoice: credit note creation date from the wizard
            :param integer date: force date from the wizard
            :param string description: description of the credit note from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the credit note
        """
        values = {}
        for field in self._get_refund_copy_fields():
            if invoice._fields[field].type == 'many2one':
                values[field] = invoice[field].id
            else:
                values[field] = invoice[field] or False

        values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)

        tax_lines = invoice.tax_line_ids
        values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)

        values['journal_id'] = journal_id.id
        values['type'] = TYPE2REFUND[invoice['type']]
        values['date_invoice'] = fields.Date.today()
        values['date_due'] = fields.Date.today()
        values['state'] = 'draft'
        values['number'] = False
        values['origin'] = invoice.reference
        values['concept'] = _("Nota de crédito por: Devolución")
        values['billing_adress'] = invoice.billing_adress or False
        values['payment_term_id'] = False
        values['refund_invoice_id'] = invoice.id
        values['authorized_voucher_id'] = self.env['sri.authorized.vouchers'].search([
            ('code', '=', '04'),
            ('type', '=', TYPEVOUCHER[invoice['type']])
        ])[0].id
        values['reference'] = False
        if invoice['type'] == 'out_invoice':
            values['point_printing_id'] = invoice.point_printing_id.id
        values['date'] = date
        return values

    @api.multi
    def add_refund(self):
        """
        Añadimos nota de crédito en factura (Este método fue mejorado para nuestra localización)
        :return:
        """
        if self.type == 'out_invoice' and self.partner_id.type_documentation == '3':
            raise UserError(_("No se puede crear nota de crédito para comprador: Consumidor final"))
        journal = self.journal_id.refund_journal_id
        if not journal:
            raise UserError(
                _("No está definido el diario para Nota de crédito en diario: %s") % self.journal_id.name)

        new_refund = self.refund(self.date_invoice, self.date_invoice, False, journal)
        new_refund.with_context(refund=True).compute_taxes()
        imd = self.env['ir.model.data']
        if self.type == 'out_invoice':
            action = imd.xmlid_to_object('account.action_invoice_out_refund')
            form_view_id = imd.xmlid_to_res_id('account.invoice_form')
        else:
            action = imd.xmlid_to_object('account.action_invoice_in_refund')
            form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if new_refund:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = new_refund.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    have_refund = fields.Boolean(compute="_compute_have_refund", string='Tiene nota de crédito?',
                                 help="Técnico: para saber si documento tiene nota de crédito.")


class Journal(models.Model):
    _inherit = 'account.journal'

    refund_journal_id = fields.Many2one('account.journal', domain=[('type', 'in', ('sale', 'purchase'))],
                                        string="Diario (nota de crédito)",
                                        help="Debemos definir diario contable para nota contabilizar nota de crédito.")
