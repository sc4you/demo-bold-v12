# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from itertools import groupby
from operator import itemgetter
from datetime import datetime, time
from itertools import groupby


class PaymentCashierReportPdf(models.AbstractModel):
    _name = 'report.eliterp_payment.report_payment_cashier'

    @api.multi
    def _get_domain(self, data):
        domain = [
            ('journal_id', 'in', data['journal_ids'].ids),
            ('payment_date', '>=', data['date_start']),
            ('payment_date', '<=', data['date_end']),
            ('state', '=', 'posted'),
            ('create_uid', 'in', data['user_ids'].ids),
            ('payment_cashier_id', '=', data['payment_cashier_id'].id)
        ]
        return domain

    def _get_retention_cashier(self, data):
        domain_retention = [
            ('state', '=', 'confirm'),
            ('date_retention', '>=', data['date_start']),
            ('date_retention', '<=', data['date_end']),
            ('create_uid', 'in', data['user_ids'].ids),
            ('type', '=', 'sale')
        ]
        retentions_cashier = self.env['account.retention'].sudo().search(domain_retention)
        return sum(x.total for x in retentions_cashier)

    def _get_refund_cashier(self, data):
        domain_refund = [
            ('state', 'in', ['open', 'paid']),
            ('date_invoice', '>=', data['date_start']),
            ('date_invoice', '<=', data['date_end']),
            ('create_uid', 'in', data['user_ids'].ids),
            ('type', '=', 'out_refund')
        ]
        refunds_cashier = self.env['account.invoice'].sudo().search(domain_refund)
        return sum(x.amount_total for x in refunds_cashier)

    @api.model
    def _get_lines(self, o):
        domain = self._get_domain(o)
        payments = self.env['account.payment'].sudo().search(domain, order='journal_id')
        data = []
        summary = []
        details = []
        for payment in payments:
            invoices = ', '.join(invoice.reference for invoice in payment.mapped('invoice_ids'))
            if not invoices and payment.payment_special_id:
                invoices = ', '.join(invoice.name for invoice in payment.payment_special_id.invoice_ids)
            bank_account = payment.partner_bank_account_id
            details.append({
                'invoice': invoices,
                'date': payment.payment_date,
                'type': "%s - %s" % (payment.journal_id.code, payment.journal_id.name),
                'amount': payment.amount,
                'reference': payment.check_number if payment.payment_method_code == 'customer_check_printing' else payment.movement_reference or 'N.A',
                'bank': bank_account.bank_id.name or '-' if bank_account else 'N.A',
                'account': bank_account.acc_number if bank_account else 'N.A',
                'user': payment.create_uid.name,
            })

        # Suma de cobros
        for type, group in groupby(details, key=itemgetter('type')):
            total = sum(x['amount'] for x in group)
            summary.append({
                'type': type,
                'amount': total
            })

        amount_refunds = self._get_refund_cashier(o)
        summary.append({
            'type': 'NCC - Nota de crédito',
            'amount': -1 * amount_refunds
        })

        amount_retentions = self._get_retention_cashier(o)
        summary.append({
            'type': 'RT - Retención',
            'amount': -1 * amount_retentions
        })

        data.append({
            'summary': summary,
            'details': details
        })
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'account.payment.cashier.report',
            'docs': self.env['account.payment.cashier.report'].browse(docids),
            'currency_precision': self.env.user.company_id.currency_id.decimal_places,
            'get_lines': self._get_lines
        }


class PaymentCashierReport(models.TransientModel):
    _name = 'account.payment.cashier.report'
    _description = _("Ventana para reporte de caja registradora")

    def _default_journals(self):
        journals = self.env['account.journal'].sudo().search([('type', 'in', ['bank', 'cash'])])
        return journals

    @api.multi
    def print_report_pdf(self):
        return self.env.ref('eliterp_payment.action_report_payment_cashier').report_action(self)


    date_start = fields.Date('Fecha inicial', required=True, default=fields.Date.today())
    date_end = fields.Date('Fecha final', required=True, default=fields.Date.today())
    payment_cashier_id = fields.Many2one('account.payment.cashier', 'Caja registradora', required=True)
    user_ids = fields.Many2many('res.users', string='Usuarios', required=True)
    journal_ids = fields.Many2many('account.journal', string="Tipo de cobro",
                                   domain=[('type', 'in', ['bank', 'cash'])], required=True, default=_default_journals)
