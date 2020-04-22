# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class Inventory(models.Model):
    _inherit = 'stock.inventory'

    name = fields.Char(
        'Referencia de inventario',
        readonly=True, required=False)  # CM

    def action_start(self):
        """
        ME: Actualizamos el nombre con la secuencia seteada en compañía
        :return:
        """
        res = super(Inventory, self).action_start()
        sequence = self.company_id.sequence_inventory_id
        if not sequence:
            raise UserError(_("No tiene prestablecida la secuencia en la compañía para Ajuste de inventario."))
        else:
            self.update({'name': sequence.next_by_id()})
        return res
