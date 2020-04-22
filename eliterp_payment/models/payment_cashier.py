# -*- coding: utf-8 -*-


from odoo import fields, models, api, _

class Users(models.Model):
    _inherit = 'res.users'

    cashier = fields.Boolean('Es cajero', default=False,
                             help="Técnico: saber si usuario puede hacer uso de caja registradora.")
    cashier_ids = fields.Many2many('account.payment.cashier', 'cashier_users_rel', 'user_id', 'model_id', string='Cajas')


class PaymentCashier(models.Model):
    _name = 'account.payment.cashier'
    _description = _("Caja registrador (Cobros)")

    name = fields.Char('Nombre de caja', index=True, required=True)
    user_ids = fields.Many2many('res.users', 'cashier_users_rel', 'model_id', 'user_id', string='Usuarios')
    payment_ids = fields.One2many('account.payment', 'payment_cashier_id', string='Cobros')

    @api.multi
    def action_view_cashier_payments(self):
        # Transacciones contabilizadas y las del día por caja
        self.ensure_one()
        action = self.env.ref('eliterp_payment.action_payments').read()[0]
        action['domain'] = [
            ('payment_cashier_id', '=', self.id)
        ]
        action['context'] = {
            'search_default_payments_today': True
        }
        return action

class Payment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _default_cashier(self):
        return

    payment_cashier_id = fields.Many2one('account.payment.cashier', 'Caja registradora', default=_default_cashier)