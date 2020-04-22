# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    send_email = fields.Boolean('Correo enviado', default=False)

    @api.multi
    def action_mass_mail_wizard(self):
        payslip_ids = []
        active_ids = self.env.context.get('active_ids', [])
        slip_ids = self.env['hr.payslip'].search([('id', 'in', active_ids)])
        for slip in slip_ids:
            if not slip.send_email and slip.state == 'done':
                payslip_ids.append(slip.id)
        action = self.env.ref('eliterp_hr_payslip_mass_email.action_payslip_mass_mail').read()[0]
        action['context'] = {'default_payslip_ids': payslip_ids}
        return action

    @api.multi
    def action_payslip_sent(self):
        self.ensure_one()
        template = self.env.ref('eliterp_hr_payslip_mass_email.mail_template_payslip')
        if template:
            self.env['mail.template'].browse(template.id).send_mail(self.id, force_send=True)
            self.send_email = True
