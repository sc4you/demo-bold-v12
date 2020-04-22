# -*- coding: utf-8 -*-

import os
from odoo import api, models, fields
from jinja2 import Environment, FileSystemLoader
from . import utils

PRODUCT_CODE = {
    'out_invoice': 'codigoPrincipal',
    'out_refund': 'codigoInterno'
}


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def copy(self, default=None):
        """
        Al duplicar colocamos el nuevo secuencial.
        :param default:
        :return:
        """
        default = default or {}
        record = super(Invoice, self).copy(default=default)
        record._onchange_point_printing_id()
        record._onchange_invoice_number()
        return record

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        """
        Generamos datos de nota de credito electronica
        :param invoice:
        :param date_invoice:
        :param date:
        :param description:
        :param journal_id:
        :return:
        """
        vals = super(Invoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        if self.type == 'out_invoice':
            invoice_number = self.point_printing_id._get_electronic_sequence('out_refund')
            vals['invoice_number'] = invoice_number.zfill(9)
        return vals

    @api.multi
    def action_invoice_open(self):
        for invoice in self.filtered(lambda x: x.is_electronic):
            invoice.action_electronic_voucher()
            invoice.point_printing_id.next(invoice.type)
        return super(Invoice, self).action_invoice_open()

    def _get_electronic_voucher(self):
        """
        Creamos documento electrónico desde 'account.invoice'
        con la clave de acceso generada.
        :return:
        """
        company = self.company_id
        electronic_voucher = self.env['sri.electronic.voucher']
        access_key = False
        if company.type_service == 'own':
            access_key = electronic_voucher.sudo()._get_access_key(
                company,
                [
                    self.point_printing_id,
                    self.date_invoice,
                    self.authorized_voucher_id.code,
                    self.invoice_number
                ]
            )
        vals = {
            'name': access_key,
            'document_id': '{0},{1}'.format('account.invoice', str(self.id)),
            'type_emission': company.type_emission,
            'environment': company.environment,
            'authorized_voucher_id': self.authorized_voucher_id.id,
            'document_date': self.date_invoice,
            'document_number': self.reference,
            'company_id': company.id
        }
        new_object = electronic_voucher.sudo().create(vals)
        return new_object

    @staticmethod
    def fix_date(date):
        d = date.strftime('%d/%m/%Y')
        return d

    @staticmethod
    def _get_iva_0(amount):
        vals = {
            'codigo': '2',
            'codigoPorcentaje': '0',
            'baseImponible': '{:.2f}'.format(amount),
            'valor': '0.00'
        }
        return vals

    @staticmethod
    def _get_line_iva_0(amount):
        vals = {
            'codigo': '2',
            'codigoPorcentaje': '0',
            'tarifa': '0',
            'baseImponible': '{:.2f}'.format(amount),
            'valor': '0.00'
        }
        return vals

    def _get_vals_total_taxes(self):
        # TODO: Revisar códigos, defecto 12%
        totalTaxes = []
        for tax in self.tax_line_ids:
            totalTax = {
                'codigo': '2',
                'codigoPorcentaje': '2',
                'baseImponible': '{:.2f}'.format(tax.base),
                'valor': '{:.2f}'.format(tax.amount)
            }
            totalTaxes.append(totalTax)
        # Si no existe ningún impuesto colocamos el de 0%
        if not totalTaxes:
            totalTaxes.append(self._get_iva_0(self.amount_untaxed))
        return {'totalImpuesto': totalTaxes}

    def _get_sri_payments(self):
        # TODO: Empresas negociables (Tienen varias formas de pago)
        sriPayment = {
            'formaPago': self.payment_form_id.code,
            'total': '{:.2f}'.format(self.amount_total),
        }
        return {'pago': [sriPayment]}

    def _get_vals_information(self):
        """
        Devolvemos la información necesaria
        para el documento XML.
        :return:
        """
        company = self.company_id
        partner = self.partner_id
        point_printing = self.point_printing_id
        informationInvoice = {
            'fechaEmision': self.fix_date(self.date_invoice),
            'dirEstablecimiento': point_printing.establishment_id.street,
            'obligadoContabilidad': 'SI',
            'tipoIdentificacionComprador': utils.table6[partner.type_documentation],
            'razonSocialComprador': partner.name,
            'identificacionComprador': partner.documentation_number,
            # TODO: 'direccionComprador': self.billing_adress,
            'totalSinImpuestos': '{:.2f}'.format(self.amount_untaxed),
            'totalDescuento': '{:.2f}'.format(self.amount_discount),
        }

        if company.special_contributor:
            informationInvoice.update({'contribuyenteEspecial': company.code_special_contributor})

        totalTaxes = self._get_vals_total_taxes()
        informationInvoice.update({'totalConImpuestos': totalTaxes})
        informationInvoice.update({
            'propina': '0.00',
            'importeTotal': '{:.2f}'.format(self.amount_total),
            'moneda': 'DOLAR'
        })
        informationInvoice.update({'pagos': self._get_sri_payments()})
        return informationInvoice

    def _get_vals_information_refund(self):
        company = self.company_id
        partner = self.partner_id
        point_printing = self.point_printing_id
        invoice = self.refund_invoice_id
        informationRefund = {
            'fechaEmision': self.fix_date(self.date_invoice),
            'dirEstablecimiento': point_printing.establishment_id.street,
            'tipoIdentificacionComprador': utils.table6[partner.type_documentation],
            'razonSocialComprador': partner.name,
            'identificacionComprador': partner.documentation_number,
            'obligadoContabilidad': 'SI',
            'codDocModificado': utils.table3[invoice.authorized_voucher_id.code],
            'numDocModificado': invoice.reference,
            'fechaEmisionDocSustento': self.fix_date(invoice.date_invoice),
            'totalSinImpuestos': '{:.2f}'.format(self.amount_untaxed),
            'valorModificacion': '{:.2f}'.format(self.amount_total),
            'moneda': 'DOLAR'
        }

        if company.special_contributor:
            informationRefund.update({'contribuyenteEspecial': company.code_special_contributor})

        totalTaxes = self._get_vals_total_taxes()
        informationRefund.update({'totalConImpuestos': totalTaxes})
        informationRefund.update({'motivo': self.concept})
        return informationRefund

    @staticmethod
    def fix_chars(code):
        special = [
            [u'%', ' '],
            [u'º', ' '],
            [u'Ñ', 'N'],
            [u'ñ', 'n'],
            [u'\n', ' '],
            [u'\r\n', '']
        ]
        for f, r in special:
            code = code.replace(f, r)
        return code

    def _get_vals_details(self):
        """
        Detalle de la factura (Líneas)
        :param invoice:
        :return:
        """
        details = []
        for line in self.invoice_line_ids:
            productCode = line.product_id and \
                          line.product_id.default_code and \
                          self.fix_chars(line.product_id.default_code) or '001'
            fix_price = self.env['account.tax']._fix_tax_included_price(line.price_unit, line.invoice_line_tax_ids, [])
            price = fix_price * (1 - (line.discount or 0.00) / 100.0)
            discount = (fix_price - price) * line.quantity
            detail = {
                PRODUCT_CODE[self.type]: productCode,
                'descripcion': self.fix_chars(line.name.strip()),
                'cantidad': '{:.4f}'.format(line.quantity),
                'precioUnitario': '{:.4f}'.format(fix_price),
                'descuento': '{:.2f}'.format(discount),
                'precioTotalSinImpuesto': '{:.2f}'.format(line.price_subtotal)
            }
            taxes = []
            # Si línea no tiene impuestos colocamos IVA 0
            if not line.invoice_line_tax_ids:
                taxes.append(self._get_line_iva_0(line.price_subtotal))
            for tax_line in line.invoice_line_tax_ids:
                amount = (line.price_subtotal * tax_line.amount) / 100
                tax = {
                    'codigo': '2',
                    'codigoPorcentaje': '2',
                    'tarifa': "%s" % int(tax_line.amount),
                    'baseImponible': '{:.2f}'.format(line.price_subtotal),
                    'valor': '{:.2f}'.format(amount)
                }
                taxes.append(tax)
            detail.update({'impuestos': {'impuesto': taxes}})
            details.append(detail)
        return {'detalle': details}

    @api.one
    def render_document(self, information_company):
        """
        Devolvemos el XML del documento actual con todos sus datos.
        :param information_company:
        :return:
        """
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        environment = Environment(loader=FileSystemLoader(template_path))
        template = environment.get_template(utils.TEMPLATES[self.type])
        data = {}
        data.update(information_company)
        if self.type == 'out_invoice':
            data.update(self._get_vals_information())
        else:
            data.update(self._get_vals_information_refund())
        data.update({'detalles': self._get_vals_details()})
        return template.render(data)

    @api.multi
    def action_electronic_voucher(self):
        """
        Método de generación de factura electrónica.
        :return:
        """
        self.ensure_one()
        electronic_voucher = self._get_electronic_voucher()
        self.write({'electronic_voucher_id': electronic_voucher.id})

    electronic_voucher_id = fields.Many2one('sri.electronic.voucher', string='Comprobante electrónico', readonly=True,
                                            copy=False)
    authorization_date = fields.Datetime(
        'Fecha autorización',
        related='electronic_voucher_id.authorization_date', store=True, readonly=True
    )
    authorization_status = fields.Selection(utils.STATES, related='electronic_voucher_id.state', readonly=True,
                                            store=True)
