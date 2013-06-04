#-------------------------------------------------------------------------------
# Name:         db_sqlite_py
# Purpose:      Для работы с базой данных SQLite
#               Предназначен для взаимодействия с БД SQLite
#               включает 3 класса:
# Author:       Цымай Дмитрий (dmitry-zy@yandex.ru)
#
# Created:      25.05.2013
# Copyright:    (c) Цымай Дмитрий 2013
# Licence:      LGPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import sqlite3
import string
import codecs
import pickle
import sys
import os
import time

def info():
    #Общая информация
    print("database 0 sqlite3 ")
    return True
    #
class Journal(object):
    #Класс для ведения журнала действий
    def __init__(self,output=True,file_name='journal'):
        self.__filename=file_name+'.out'
        self.__out=[]
        self.restore()
    #
    def __del__(self):
        #Очистка всех записей
        self.save()
        print self.__out
    #
    def clear(self):
        self.__out=[]
        self.save()
    #
    def getJournal(self):
        #возвращает список ошибок
        #
        return self.__out
        #
    def save(self):
        #Запись результатов вывода в файл
        #
        f_out=open(self.__filename,"w")
        rec_str=pickle.dump(self.__out,f_out)
        f_out.close()
        #
    def restore(self):
        #Восстановление результатов вывода из файла
        #
        f_in=open(self.__filename,"r")
        rec_str=pickle.load(f_in)
        for rec in rec_str:
            self.__out.append(rec)
        #
    def add(self,metod,comment,zapros):
        #Внесение комментария в список
        #
        #metod метод
        #comment комментарий
        #zapros текст запроса
        #
        tm=time.asctime()
        self.__out.append((tm,metod,comment,zapros))
        self.save()
        return len(self.__out)
#
#
#
class set_info(object):
    def __init__(self,dbname,path):
        self.dbname=dbname
        self.path=path
#
#
#
class database(set_info):
    #соединение с файлом базы данных sqlite  и отправка запросов
    def __init__(self,dbname=None,path=None):
        #Начальные значения переменных
        #
        set_info.__init__(self,dbname,path)
        #Путь к БД
        if (dbname!=None)and(os.path.exists(path+dbname)):
            self.dbname=path+dbname
        #Результат последнего запроса
        self.result=None
        #Список ошибок
        self.__errorlist=Journal(True,'error')
        #
    def _execute(self,zapros,param=None):
        #Выполнение запроса к БД
        #zapros-запрос
        #param-параметры запроса кортеж переменных заменяющих в запросе знаки ?
        #
        res=False
        #
        if param==None: param=()
        # Проверка существования файла БД
        if self.dbname!=None:
            conn=sqlite3.connect(self.dbname)
            cursor=conn.cursor()
            try:
                cursor.execute(zapros,param)
            except:
                self.__errorlist.add('execute','Некорректный запрос',zapros)
            conn.commit()
            #количество полученных записей
            self.__rcount=cursor.rowcount
            self.result=cursor.fetchall()
            #закрываем соединение
            cursor.close()
            conn.close()
            if len(self.result)>0:
                res=self.result
        return res
    #
    def get_tables(self):
        #Список таблиц в БД
        #
        zapros='SELECT "name" from "sqlite_master"'
        self._execute(zapros)
        res=[x[0] for x in self.result]
        return res
    #
    def exists_tables(self,table_name):
        #проверка, существует ли таблица в базе данных
        #
        #table_name - имя таблицы
        #
        if table_name in self.get_tables(): res=True
        else: res=False
        return res
    #
    def get_tables_info(self,table_name):
        #Полная информация о таблице
        #
        #table_name=None - имя таблицы
        #
        zapros='PRAGMA table_info ('+table_name+')'
        res=[]
        [res.append([x[1],x[2]]) for x in self._execute(zapros)]
        return res
    #
    def create_table(self,table_name,fld_type):
        #Создание таблицы
        #
        #table_name=None - имя таблицы
        #fld_type Словарь с именами и типами полей таблицы
        #
        res=False
        if isinstance(fld_type,dict) and (not self.exists_tables(table_name)):
            fld=['"'+f+'" '+t  for f,t in fld_type.items()]
            zapros='CREATE TABLE "'+table_name+'"('+string.join(fld,',')+')'
            if self._execute(zapros)!=False:
                self.__errorlist.add('create','Создана таблица '+table_name,zapros)
                res=True
        return res
        #
    def delete_table(self,table_name):
        #Удаление таблицы
        #
        #table_name=None - имя таблицы
        #
        res=False
        if self.exists_tables(table_name):
            zapros='DROP TABLE "'+table_name+'"'
            if self._execute(zapros,())!=False:
                self.__errorlist.add('delete','Удалена таблица: '+table_name,zapros)
                res=True
        else:
            self.__errorlist.add('delete','Таблица: '+table_name+' не существует',zapros)
        return res
#
#
#
class tables(database):
    #работа с таблицей из БД
    #
    def __init__(self,dbname=None,path=None,table_name=None):
        #БД по умолчанию
        database.__init__(self,dbname,path)
        #Начальные значения переменных
        #Журнал действий
        self.__log=Journal(True,'log')
        #Имя текущей таблицы
        self.set_table_name(table_name)
    #
    def insert(self,fld_nm_val):
        #Вставка в таблицу
        #
        #fld_nm_val-словарь {'param_name': param_value}
        #Компоновка запроса
        table_name=self.table_name
        #
        res=False
        if table_name:
            fld_nm_val=self._validate_filds_name(fld_nm_val)
            #
            if fld_nm_val!=False:
                param,fld=[],[]
                for f,v in fld_nm_val.items():
                    param.append(v)
                    fld.append(f)
                param=tuple(param)
                fld=u'('+string.join(fld,u',')+u')'
                val=u'('+string.join(["?"]*len(fld_nm_val),u',')+u')'
                #
                zapros=u'INSERT INTO '+table_name+fld+u' VALUES'+val
                zapros=codecs.utf_8_decode(zapros)[0]
                #
                res=self._execute(zapros,param)
        return res
    #
    def select(self,where='1=1',filds='*'):
        #Выборка из таблицы
        #
        #where='1=1' - условие
        #filds='*' - список полей []
        #
        table_name=self.table_name
        #
        res=False
        if table_name:
            filds=self._validate_filds_name(filds)
            if filds==False:
                filds='*'
            elif isinstance(filds,list):
                filds=string.join(filds,',')
            #
            zapros=u'SELECT '+filds+u' from '+table_name+u' WHERE '+where
            zapros=codecs.utf_8_decode(zapros)[0]
            #
            res=self._execute(zapros)
        return res
    #
    def update(self,fld_nm_val,where):
        #Обновление записи
        #
        #where - условие
        #fld_nm_val-словарь {'param_name': param_value}
        #
        table_name=self.table_name
        #
        res=False
        if table_name:
            fld_nm_val=self._validate_filds_name(fld_nm_val)
            if fld_nm_val!=False:
                #Компоновка запроса
                param,fld=[],[]
                for f,v in fld_nm_val.items():
                    param.append(v)
                    fld.append(f+'=?')
                param=tuple(param)
                fld=string.join(fld,',')
                #
                zapros=u'UPDATE '+table_name+u' SET '+fld+u' WHERE '+where
                zapros=codecs.utf_8_decode(zapros)[0]
                #
                res=self._execute(zapros,param)
        return res
    #
    def delete(self,where):
        #удаление записи
        #
        #where - условие
        #
        table_name=self.table_name
        #
        res=False
        if table_name:
            zapros='DELETE from '+table_name+' WHERE '+where
            zapros=codecs.utf_8_decode(zapros)[0]
            res=self._execute(zapros)
            #
        return res
    #
    def count(self):
        #Количество записей в текущей таблице
        #
        res=self.select()
        if res:
            return len(res)
        else:
            return 0
    #
    def set_table_name(self,table_name):
        #Открыть новую таблицу
        #
        #table_name=None - имя таблицы
        #
        if self.exists_tables(table_name):
            self.__log.add('open table',u'Открыта таблица "'+table_name+u'" в базе данных "'+self.dbname+u'"','')
            self.table_name=table_name
            self.filds_name_type=self.get_tables_info(self.table_name)
            self.filds_name=[x[0] for x in self.filds_name_type]
            result=True
        else:
            self.__log.add('open table',u'Таблица "'+table_name+u'" в базе данных "'+self.dbname+u'" не существует','')
            self.table_name=None
            result=False
        return result
    #
    def _validate_filds_name(self,filds):
        #проверка имени поля
        #
        #filds - словарь {fild_name:fild_value} или список имен полей
        #
        #если проверяется словарь
        if isinstance(filds,dict):
            del_fld=[fld for fld in filds.keys() if not(fld in self.filds_name)]
            for fld in del_fld:
                del filds[fld]
            if len(filds)==0: filds=False
        #Если проверяется список
        elif isinstance(filds,list):
            filds=[fld for fld in filds if fld in self.filds_name]
            if len(filds)==0: filds=False
        #если проверяется строка
        elif isinstance(filds,str):
            if not(filds in self.filds_name): filds=False
        else: filds=False
        #возврат словаря/списка/строки соответствующих полям в таблице
        return filds
    #
    def _validate_filds_value(self,fld_name,fld_value):
        #Проверка fld_name записи
        #
        #fld_name - имя поля
        #fld_value - значение
        #
        res_qwery=self.select(filds=fld_name)
        if res_qwery:
            fld_value_table=[x[0] for x in res_qwery]
            if fld_value in fld_value_table:
                return True
            else:
                return False
        else:
            return False
    #
    def _last_insert_id(self):
        #id последней вставленной записи
        #
        zapros='SELECT MAX(id) FROM "'+self.table_name+'"'
        return self._execute(zapros)[0][0]
    #
def main():
    info()
    table=tables('term_base.sqlite',os.path.abspath('.'),'oxidetepl')
    res=table.create_table('test1',{'n1':'stri','n2':'int'})
    res=table.select('subst="'+'MgO'+'"',["subst","dt1","dt2","dh298","da","db","dc","dd","ds298","uat0","m_coeff","n_coeff","dhh298","dhfp","z_coeff"])

    print res

if __name__ == '__main__':
    main()
    #
