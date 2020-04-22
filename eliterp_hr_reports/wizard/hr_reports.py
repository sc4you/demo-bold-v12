# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class ReportHelpFunctions(models.AbstractModel):
    _name = 'hr.report.help.functions'
    _description = _("Funciones de ayuda para reportes contables")

    start_date = fields.Date('Fecha inicio', required=True)
    end_date = fields.Date('Fecha fin', required=True)
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.user.company_id)


class EmployeeReportPdf(models.AbstractModel):
    _name = 'report.eliterp_hr_reports.report_employee_report'

    @staticmethod
    def _get_civil_status(civil_status):
        """
        Retornamos el estado civil en español (.po)
        :param civil_status:
        :return: string
        """
        if civil_status == 'single':
            return "Soltero(a)"
        elif civil_status == 'married':
            return "Casado(a)"
        elif civil_status == 'widower':
            return "Viudo(a)"
        elif civil_status == 'divorced':
            return "Divorciado(a)"
        else:
            return 'Unión libre'

    def _get_lines(self, doc):
        """
        Obtenemos líneas de reporte
        :param doc:
        :return: list
        """
        data = []
        arg = []
        arg.append(('admission_date', '>=', doc['start_date']))
        arg.append(('admission_date', '<=', doc['end_date']))
        employees = self.env['hr.employee'].search(arg)
        for employee in employees:
            if employee.id == 1:  # Empleado id=1 no va (Crea el sistema por al realizar la implementación)
                continue
            data.append({
                'name': employee.name,
                'identification_id': employee.identification_id,
                'age': employee.age if employee.birthday else '-',
                'civil_status': self._get_civil_status(employee.marital) if employee.marital else '-',
                'admission_date': employee.admission_date,
                'job_id': employee.job_id.name if employee.job_id else '-',
                'wage': employee.contract_id.wage if employee.contract_id else '-',
                'struct_id': employee.contract_id.struct_id.code if employee.contract_id else '-',
                'bank_account': '{0} [{1}]'.format(employee.bank_account_id.bank_name, employee.bank_account_id.acc_number) if employee.bank_account_id else '-'
            })
        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee.report',
            'docs': self.env['hr.employee.report'].browse(docids),
            'get_lines': self._get_lines
        }


class StatusResults(models.TransientModel):
    _name = 'hr.employee.report'
    _inherit = ['report.xlsx.abstract', 'hr.report.help.functions']
    _description = _("Ventana para reporte de empleados")

    def generate_xlsx_report(self, workbook, context):
        lines_4 = self._get_lines_type(context, '4')
        lines_5 = self._get_lines_type(context, '5')
        sheet = workbook.add_worksheet('Estado de resultados')
        # Columnas
        sheet.set_column("A:A", 15)
        sheet.set_column("B:B", 50)
        sheet.set_column("C:C", 10)
        sheet.set_column("D:D", 15)
        sheet.autofilter('A3:D3')
        # Formatos
        title = workbook.add_format({
            'bold': True,
            'border': 1
        })
        heading = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'align': 'center',
            'border': 1
        })
        heading_1 = workbook.add_format({
            'bold': True,
            'font_size': 11
        })
        heading_1_number = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'num_format': '#,##0.00'
        })
        heading_2 = workbook.add_format({
            'font_size': 9,
            'bold': True,
        })
        heading_2_number = workbook.add_format({
            'font_size': 9,
            'bold': True,
            'num_format': '#,##0.00'
        })
        heading_3 = workbook.add_format({
            'font_size': 8,
        })
        heading_3_number = workbook.add_format({
            'font_size': 8,
            'num_format': '#,##0.00'
        })
        # Formatos de celda
        sheet.write('A1', 'ESTADO DE RESULTADOS', title)
        columns = [
            'CÓDIGO', 'NOMBRE DE CUENTA', 'TIPO', 'BALANCE'
        ]
        row = 2
        col = 0
        for column in columns:
            sheet.write(row, col, column, heading)
            col += 1
        # 4
        row += 1
        for line in lines_4:
            if line['type'] == 'principal':
                sheet.write(row, 0, line['code'], heading_1)
                sheet.write(row, 1, line['name'], heading_1)
                sheet.write(row, 3, line['amount'], heading_1_number)
                row += 1
            else:
                sheet.write(row, 0, line['code'], heading_2)
                sheet.write(row, 1, line['name'], heading_2)
                sheet.write(row, 2, 'VISTA', heading_2)
                sheet.write(row, 3, line['amount'], heading_2_number)
                if line['subaccounts']:
                    for lsb in line['subaccounts']:
                        if float_is_zero(lsb['amount'], precision_rounding=0.01):
                            continue
                        row += 1
                        sheet.write(row, 0, lsb['code'], heading_3)
                        sheet.write(row, 1, lsb['name'], heading_3)
                        sheet.write(row, 2, 'Movimiento', heading_3)
                        sheet.write(row, 3, lsb['amount'], heading_3_number)
                row += 1
        # 5
        for line in lines_5:
            if line['type'] == 'principal':
                sheet.write(row, 0, line['code'], heading_1)
                sheet.write(row, 1, line['name'], heading_1)
                sheet.write(row, 3, line['amount'], heading_1_number)
                row += 1
            else:
                sheet.write(row, 0, line['code'], heading_2)
                sheet.write(row, 1, line['name'], heading_2)
                sheet.write(row, 2, 'VISTA', heading_2)
                sheet.write(row, 3, line['amount'], heading_2_number)
                if line['subaccounts']:
                    for lsb in line['subaccounts']:
                        if float_is_zero(lsb['amount'], precision_rounding=0.01):
                            continue
                        row += 1
                        sheet.write(row, 0, lsb['code'], heading_3)
                        sheet.write(row, 1, lsb['name'], heading_3)
                        sheet.write(row, 2, 'MOVIMIENTO', heading_3)
                        sheet.write(row, 3, lsb['amount'], heading_3_number)
                row += 1
        row += 1
        amount_4 = lines_4[0]['amount'] if lines_4 else 0.00
        amount_5 = lines_5[0]['amount'] if lines_5 else 0.00
        amount_total = amount_4 - amount_5
        heading_result_number = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'num_format': '#,##0.00',
            'bg_color': 'red'
        })
        if amount_total > 0:
            sheet.write(row, 3, amount_total, heading_1)
        else:
            sheet.write(row, 3, amount_total, heading_result_number)

    @api.multi
    def print_report_xlsx(self):
        """
        Imprimimos reporte en xlsx
        :return:
        """
        context = dict(
            company_id=self.company_id,
            start_date=self.start_date,
            end_date=self.end_date
        )
        self.write(self.create_xlsx_report('Empleados', context))
        return {
            'name': "Reporte de empleados",
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.report',
            'view_mode': ' form',
            'view_type': ' form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.multi
    def print_report_pdf(self):
        """
        Imprimimos reporte en pdf
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr_reports.action_report_employee').report_action(self)
