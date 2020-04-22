# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
import base64
from odoo.exceptions import UserError
from io import StringIO
import csv


class Payment(models.Model):
    _inherit = 'account.payment'

    @staticmethod
    def replaceMultiple(mainString, toBeReplaces, newString):
        """
        Reemplazar varios string en cadena
        :param mainString:
        :param toBeReplaces:
        :param newString:
        :return:
        """
        for elem in toBeReplaces:
            if elem in mainString:
                mainString = mainString.replace(elem, newString)
        return mainString

    def _verify_account_employee(self, employees):
        """
        Verificamos qué empleados tengan cuentas bancarias configuradas
        :param employees:
        :return:
        """
        message = ''
        for employee in employees.filtered(lambda x: not x.name.bank_account_id):
            text = "Empleado %s no tiene cuenta bancaria configurada.\n" % employee.name.name
            message += text
        if message:
            raise UserError(message)

    @api.multi
    def action_payment_template(self):
        """
        Generamos archivo para banco
        40 - BANCO BOLIVARIANO
        13 - BANCO PICHINCHA
        XXX - BANCO PRODUBANCO
        \t TAB
        \r\n ENTER
        """
        content = ""
        bank = self.journal_id.bank_id
        order = self.pay_order_id
        employees = order.employee_ids.sorted(key=lambda x: x.name.name)
        self._verify_account_employee(employees)
        if bank.bic == '40':
            count = 1
            name = 'PLANTILLA_%s%s%s_1221.biz' % (self.payment_date.year, self.payment_date.month, self.payment_date.day)
            for line in employees:
                bank_employee = line.name.bank_account_id
                content += "BZDET%s%s\t\tC%s\t\t%s\t\t%s001%s04%s\t\t1%s%s\t\t%s\t\tRPA\t\t07685007685\r\n" % (
                    str(count).zfill(6), line.name.identification_id,
                    line.name.identification_id,
                    line.name.name,
                    'COB' if bank_employee.bank_id.bic != '34' else 'CUE', bank_employee.bank_id.bic,
                    bank_employee.acc_number,
                    ("{0:.2f}".format(line.amount).replace('.', '')).zfill(15), self.reference,
                    ''.zfill(65),
                )
                count += 1
            return self.write({
                'template_filename': name,
                'template_binary': base64.b64encode(bytes(content, 'utf-8'))
            })
        elif bank.bic == '13':
            file = StringIO()
            name = 'PLANTILLA_%s.csv' % self.reference
            writer = csv.writer(file, delimiter=';')
            for line in employees:
                bank_employee = line.name.bank_account_id
                row = []
                row.append("PA")
                row.append(line.name.identification_id)
                row.append("USD")
                row.append("{0:.2f}".format(line.amount).replace('.', ''))
                row.append("CTA")
                row.append("AHO")
                row.append(bank_employee.acc_number)
                row.append(self.reference)
                row.append("C")
                row.append(line.name.identification_id)
                row.append(line.name.name)
                row.append(bank_employee.bank_id.bic)
                writer.writerow(row)
            return self.write({
                'template_filename': name,
                'template_binary': base64.b64encode(bytes(file.getvalue(), 'latin-1'))
            })
        elif bank.bic == 'XXX':
            file = StringIO()
            format_date = self.payment_date.strftime("%d%m%y")
            name = 'PLANTILLA_%s.csv' % format_date
            writer = csv.writer(file, delimiter=';')
            my_account = self.journal_id.bank_account_id
            total = self.replaceMultiple(str(self.amount), [',', '.'] , "")
            company = my_account.acc_number + total.zfill(14) + format_date + "N"
            writer.writerow(["D%s" % my_account.acc_holder_name, company])
            for line in employees:
                bank_employee = line.name.bank_account_id
                row = []
                row.append("C%s" % line.name.name)
                amount = self.replaceMultiple(str(line.amount), [',', '.'] , "")
                column = bank_employee.acc_number + amount.zfill(14) + format_date + "N"
                row.append(column)
                writer.writerow(row)
            return self.write({
                'template_filename': name,
                'template_binary': base64.b64encode(bytes(file.getvalue(), 'latin-1'))
            })
        else:
            return

    @api.one
    @api.depends('journal_id', 'type_pay_order', 'state')
    def _compute_exist_template(self):
        if self.type_pay_order in ['salary advance',
                                   'payslip run'] and self.journal_id.type == 'bank' and self.journal_id.bank_id:
            self.exist_template = self.journal_id.bank_id.generate_payroll_payment

    exist_template = fields.Boolean(compute='_compute_exist_template', string='Plantilla de pago',
                                    help="Técnico: campo para verificar si se puede generar plantilla de pago para bancos.")
    template_filename = fields.Char('Nombre de archivo')
    template_binary = fields.Binary('Archivo para banco', readonly=True)
