# -*- coding: utf-8 -*-


from odoo import api, fields, models


class PayslipMassMail(models.TransientModel):
    _name = "hr.payslip.mass.mail"

    payslip_ids = fields.Many2many('hr.payslip', string="Roles")

    @api.multi
    def action_send_mass_mail(self):
        for slip in self.payslip_ids:
            email_action = slip.action_payslip_sent()
            if email_action and email_action.get('context'):
                email_ctx = email_action['context']
                email_ctx.update(default_email_from=slip.company_id.email)
                slip.with_context(email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        return True
