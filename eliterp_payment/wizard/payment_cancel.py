# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class Payment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def action_button_cancel(self):
        return {
            'name': _("Explique la razón"),
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.payment.cancel',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class PayemntCancel(models.TransientModel):
    _name = 'account.payment.cancel'
    _description = _("Ventana para anular pago")

    description = fields.Text('Descripción', required=True)

    @api.multi
    def confirm_cancel(self):
        """
        Confirmamos la anuación del pago
        :return:
        """
        payment = self.env['account.payment'].browse(self._context['active_id'])
        payment.with_context(cancel_ref=self.description).cancel()
        return True
