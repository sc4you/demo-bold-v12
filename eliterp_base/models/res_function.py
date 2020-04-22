# -*- coding: utf-8 -*-).

from odoo import models, tools, fields, _
import babel
from datetime import datetime
import time
from dateutil import relativedelta
import math

UNIDADES = (
    '', 'Un ', 'Dos ', 'Tres ', 'Cuatro ', 'Cinco ', 'Seis ', 'Siete ', 'Ocho ', 'Nueve ', 'Diez ', 'Once ',
    'Doce ',
    'Trece ', 'Catorce ', 'Quince ', 'Dieciséis ', 'Diecisiete ', 'Dieciocho ', 'Diecinueve ', 'Veinte ')
DECENAS = ('Veinti', 'Treinta ', 'Cuarenta ', 'Cincuenta ', 'Sesenta ', 'Setenta ', 'Ochenta ', 'Noventa ', 'Cien ')
CENTENAS = (
    'Ciento ', 'Doscientos ', 'Trescientos ', 'Cuatrocientos ', 'Quinientos ', 'Seiscientos ', 'Setecientos ',
    'Ochocientos ', 'Novecientos ')


class Function(models.AbstractModel):
    _name = 'res.function'
    _description = _("Funciones de ayuda")

    def _get_amount_letters(self, amount):
        """
        Función para transformar cantidad a cantidad en letras
        :param amount:
        :return string:
        """
        currency = self.env.ref('base.USD')
        text = currency[0].amount_to_text(amount).replace('Dollars', 'Dólares')
        text = text.replace('Cents', 'Centavos')
        return text

    def _get_period_string(self, date):
        """
        Función para devolver el período tipo MMMM[y] de una fecha
        :param date:
        :return string:
        """
        ttyme = datetime.fromtimestamp(time.mktime(date.timetuple()))
        locale = self.env.context.get('lang') or 'es_EC'
        period_string = tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM [y]', locale=locale)).title()
        return period_string

    @staticmethod
    def _get_days_format_ymd(admission_date):
        """
        Número de días en formato Años, Meses y días
        # TODO: Mejorar para presentación con mayor detalle
        :param days:
        :return: string
        """
        now = fields.Datetime.now()
        admission = datetime.combine(admission_date, datetime.min.time())
        diff = now - admission
        # years = diff.years
        # months = diff.months
        days = diff.days
        # {0} años {1} meses {2} días
        return '{0} días'.format(days)

    def _get_month_name(self, date):
        ttyme = datetime.fromtimestamp(time.mktime(date.timetuple()))
        locale = self.env.context.get('lang') or 'es_EC'
        format = tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM', locale=locale))
        return format

    def _get_date_format_1(self, date):
        return '%s de %s de %s' % (date.day, self._get_month_name(date), date.year)

    def __convertNumber(self, n):
        output = ''
        if n == '100':
            output = "Cien "
        elif n[0] != '0':
            output = CENTENAS[int(n[0]) - 1]
        k = int(n[1:])
        if (k <= 20):
            output += UNIDADES[k]
        else:
            if ((k > 30) & (n[2] != '0')):
                output += '%sy %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
            else:
                output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
        return output

    def Numero_a_Texto(self, number_in):
        convertido = ''
        number_str = str(number_in) if (type(number_in) != 'str') else number_in
        number_str = number_str.zfill(9)
        millones, miles, cientos = number_str[:3], number_str[3:6], number_str[6:]
        if (millones):
            if (millones == '001'):
                convertido += 'Un Millon '
            elif (int(millones) > 0):
                convertido += '%sMillones ' % self.__convertNumber(millones)
        if (miles):
            if (miles == '001'):
                convertido += 'Mil '
            elif (int(miles) > 0):
                convertido += '%sMil ' % self.__convertNumber(miles)
        if (cientos):
            if (cientos == '001'):
                convertido += 'Un '
            elif (int(cientos) > 0):
                convertido += '%s ' % self.__convertNumber(cientos)
        return convertido

    def get_amount_to_word(self, j):
        try:
            Arreglo1 = str(j).split(',')
            Arreglo2 = str(j).split('.')
            if (len(Arreglo1) > len(Arreglo2) or len(Arreglo1) == len(Arreglo2)):
                Arreglo = Arreglo1
            else:
                Arreglo = Arreglo2

            if (len(Arreglo) == 2):
                whole = math.floor(j)
                frac = j - whole
                num = str("{0:.2f}".format(frac))[2:]
                return (self.Numero_a_Texto(Arreglo[0]) + 'con ' + num + "/100").capitalize()
            elif (len(Arreglo) == 1):
                return (self.Numero_a_Texto(Arreglo[0]) + 'con ' + '00/100').capitalize()
        except ValueError:
            return "Cero"
