# -*- coding: utf-8 -*-


from odoo import api, models, _


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @staticmethod
    def _get_rules_report(rule_ids_report):
        values = []
        new_values = []
        rule_ids_report_order = sorted(rule_ids_report, key=lambda a: a.salary_rule_id.sequence)
        for head in rule_ids_report_order:
            values.append(head.code)
        for value in values:
            if value not in new_values:
                new_values.append(value)
        return new_values

    @api.model
    def _get_lines_report(self):
        data = dict()
        body = []
        rule_ids_report = self.env['hr.payslip.line'].search([
            ('slip_id', 'in', self.slip_ids.ids),
            ('salary_rule_id.appears_on_payslip_run', '=', True)
        ])
        values = self._get_rules_report(rule_ids_report)

        thead = dict()
        thead[str(1)] = _('EMPLEADO')
        thead[str(2)] = _('IDENTIFICACIÓN')
        thead[str(3)] = _('D. TRABAJADOS')
        column = 4
        for th in values:
            column += 1
            thead[str(column)] = th

        for slip in self.slip_ids:
            row = dict()
            row['NAME'] = slip.employee_id.name
            row['IDENTIFICATION'] = slip.employee_id.identification_id
            row['WORKED_DAYS'] = slip.worked_days
            for value in values:
                result = 0.00
                for line in slip.line_ids:
                    if line.code == value:
                        result = line.total
                row[value] = result
            body.append(row)

        data['head'] = thead
        data['body'] = body
        return data
