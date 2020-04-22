# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.multi
    def _get_parent_category(self):
        """
        Obtenemos la categoría padre
        :return:
        """
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_category()
        return parent + self


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _get_pos_category(self, categ_id):
        """
        Obtenemos el nombre de la categoría padre
        :return:
        """
        categ = self.env['product.category'].browse(categ_id)
        return list(set(categ._get_parent_category()))[-1].name

    @api.multi
    def _create_pos_category(self, name):
        """
        Creamos categoría de pos si no existe
        :param name:
        :return:
        """
        PosCategory = self.env['pos.category']
        pos_category = PosCategory .search([('name', '=', name)])
        if pos_category:
            return pos_category.id
        pos_category = PosCategory .create({'name': name})
        return pos_category.id

    @api.model_create_multi
    def create(self, vals_list):
        """
        ME: Al crear producto si es PdV creamos a el vuelo la misma categoría del POS
        :param vals_list:
        :return:
        """
        for values in vals_list:
            if 'categ_id' in values and 'available_in_pos' in values:
                if values['available_in_pos']:
                    categ_name = self._get_pos_category(values['categ_id'])
                    values['pos_categ_id'] = self._create_pos_category(categ_name)
        return super(ProductTemplate, self).create(vals_list)

    @api.multi
    def write(self, values):
        if 'categ_id' in values and 'available_in_pos' in values:
            if 'available_in_pos' and values['categ_id'] != self.categ_id:
                categ_name = self._get_pos_category(values['categ_id'])
                values['pos_categ_id'] = self._create_pos_category(categ_name)
        return super(ProductTemplate, self).write(values)

    @api.onchange('type', 'sale_ok')
    def _onchange_product_type(self):
        """
        Colocamos en verdadero campo 'Disponible en PdV'
        :return:
        """
        if self.type == 'product' and self.sale_ok:
            self.available_in_pos = True
        else:
            self.available_in_pos = False
