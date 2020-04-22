# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ReportPosOder(models.AbstractModel):
    _name = 'report.eliterp_pos_reports.report_posorder'
    _description = 'Ventas POS'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, configs=False):
        """ Serialise the orders of the day information

        params: date_start, date_stop string representing the datetime of order
        """
        if not configs:
            configs = self.env['pos.config'].search([])

        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        today = today.astimezone(pytz.timezone('UTC'))
        if date_start:
            date_start = fields.Datetime.from_string(date_start)
        else:
            # start by default today 00:00:00
            date_start = today

        if date_stop:
            # set time to 23:59:59
            date_stop = fields.Datetime.from_string(date_stop)
        else:
            # stop by default today 23:59:59
            date_stop = today + timedelta(days=1, seconds=-1)

        # avoid a date_stop smaller than date_start
        date_stop = max(date_stop, date_start)

        date_start = fields.Datetime.to_string(date_start)
        date_stop = fields.Datetime.to_string(date_stop)

        orders = self.env['pos.order'].search([
            ('date_order', '>=', date_start),
            ('date_order', '<=', date_stop),
            ('state', 'in', ['paid', 'invoiced', 'done']),
            ('config_id', 'in', configs.ids)])

        user_currency = self.env.user.company_id.currency_id

        amount_total = 0.0
        OrdersList = []
        products_sold = {}
        taxes = {}
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                amount_total += order.pricelist_id.currency_id._convert(
                    order.amount_total, user_currency, order.company_id, order.date_order or fields.Date.today())
            else:
                amount_total += order.amount_total
            currency = order.session_id.currency_id
            for line in order.lines:
                key = (line.product_id, line.price_unit, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty,
                        product=line.product_id, partner=line.order_id.partner_id or False)
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0})
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                else:
                    taxes.setdefault(0, {'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0})
                    taxes[0]['base_amount'] += line.price_subtotal_incl
            OrdersList.append({
                'date': order.date_order - timedelta(hours=5),
                'config_id': order.config_id.name,
                'salesman': order.user_id.name,
                'amount_total': order.amount_total,
                'products': sorted([{
                    'product_name': product.name,
                    'quantity': qty,
                    'code': product.default_code,
                    'price_unit': price_unit,
                    'discount': discount,
                    'product_id': product.id,
                    'uom': product.uom_id.name
                } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
            })

        return {
            'currency_precision': user_currency.decimal_places,
            'amount_total': user_currency.round(amount_total),
            'company_name': self.env.user.company_id.name,
            'orders': OrdersList
        }

    @api.multi
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        configs = self.env['pos.config'].browse(data['config_ids'])
        data.update(self.get_sale_details(data['date_start'], data['date_stop'], configs))
        return data


class PosOrderWizard(models.TransientModel):
    _name = 'pos.order.wizard'
    _description = 'Reporte de ventas POS'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        # restrict to configs available to the user
        config_ids = self.env['pos.config'].search([]).ids
        # exclude configs has not been opened for 2 days
        self.env.cr.execute("""
            SELECT
            max(start_at) as start,
            config_id
            FROM pos_session
            WHERE config_id = ANY(%s)
            AND start_at > (NOW() - INTERVAL '2 DAYS')
            GROUP BY config_id
        """, (config_ids,))
        latest_start_dates = [res['start'] for res in self.env.cr.dictfetchall()]
        # earliest of the latest sessions
        return latest_start_dates and min(latest_start_dates) or fields.Datetime.now()

    start_date = fields.Datetime('Fecha inicio', required=True, default=_default_start_date)
    end_date = fields.Datetime('Fecha fin', required=True, default=fields.Datetime.now)
    pos_config_ids = fields.Many2many('pos.config', default=lambda s: s.env['pos.config'].search([]),
                                      string='Puntos de venta')

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    @api.multi
    def generate_report(self):
        if not self.env.user.company_id.logo:
            raise UserError(_("You have to set a logo or a layout for your company."))
        elif not self.env.user.company_id.external_report_layout_id:
            raise UserError(_("You have to set your reports's header and footer layout."))
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids}
        return self.env.ref('eliterp_pos_reports.pos_sale_report').report_action([], data=data)
