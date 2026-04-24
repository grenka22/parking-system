"""Инициализация приложения parking.

Настраивает pymysql как драйвер MySQL для Django.
"""

import pymysql

pymysql.install_as_MySQLdb()