#-------------------------------------------------------------------------------
# Name:         db_sqlite_py
# Purpose:      Для работы с базой данных SQLite
#               Предназначен для взаимодействия с БД SQLite
#               включает 4 класса:
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
#
def info():
    '''Общая информация'''
    print("database 0 sqlite3 ")
    return True
    #
class Journal(object):
    '''Класс для ведения журнала действий'''
    def __init__(self,output=True,file_name='journal'):
        self.__filename=file_name+'.out'
        self.__out=[]
        self.output=output
        if self.output:
            self.restore()
    #
    def __del__(self):
        #Запись в файл
        self.save()
        #self.getJournal()
    #
    def clear(self):
        #Очистка всех записей
        self.__out=[]
        self.save()
    #
    def getJournal(self):
        #возвращает список ошибок
        #
        if self.output:
            print(self.__out)
        return self.__out
        #
    def save(self):
        #Запись результатов вывода в файл
        #
        with open(self.__filename,"wb") as f_out:
            rec_str=pickle.dump(self.__out,f_out)
        #
    def restore(self):
        #Восстановление результатов вывода из файла
        #
        with open(self.__filename,'rb') as f_in:
            self.__out=pickle.load(f_in)
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
        return len(self.__out)
#
#
#
class set_info(object):
    def __init__(self,dbname,path):
        self.dbname=dbname
        self.path=path
        #Результат последнего запроса
        self.result=None
        #Список ошибок
        self.log=Journal(False,'error')
        self.error=False
    #
    def _execute(self,zapros,param=None):
        '''Выполнение запроса к БД
        zapros-запрос
        param-параметры запроса кортеж переменных заменяющих в запросе знаки ?
        '''
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
                self.log.add('execute','Некорректный запрос',zapros)
                self.error=True
            conn.commit()
            #количество полученных записей
            self.__rcount=cursor.rowcount
            self.result=cursor.fetchall()
            #закрываем соединение
            cursor.close()
            conn.close()
            if self.result:
                res=self.result
        return res
    #
#
#
#
class database(set_info):
    '''соединение с файлом базы данных sqlite  и отправка запросов'''
    def __init__(self,dbname=None,path=None):
        #Начальные значения переменных
        #
        set_info.__init__(self,dbname,path)
        #Путь к БД
        if (dbname!=None)and(os.path.exists(path+dbname)):
            self.dbname=path+dbname
        #
    def list_tables(self):
        '''Список таблиц в БД'''
        #
        zapros='SELECT "name" from "sqlite_master"'
        self._execute(zapros)
        res=[x[0] for x in self.result]
        return res
    #
    def get_table(self,table_name):
        '''Получить ссылку на таблицу
           table_name - имя таблицы'''
        #
        if self.exists_tables(table_name):
            filds_name_type=self.get_tables_info(table_name)
            newtbl=tables(self.dbname,self.path,table_name,filds_name_type,True)
            self.log.add('open table','Открыта таблица "{0}" в базе данных "{1}"'.format(table_name,self.dbname),'')
        else:
            newtbl=False
            self.log.add('open table','Таблица "{0}" в базе данных "{1}" не существует'.format(table_name,self.dbname),'')
        return newtbl
    #
    def exists_tables(self,table_name):
        '''Проверка, существует ли таблица в базе данных
        table_name - имя таблицы'''
        #
        if table_name in self.list_tables():
            res=True
        else:
            res=False
        return res
    #
    def get_tables_info(self,table_name):
        '''Полная информация о таблице
        table_name=None - имя таблицы'''
        #
        zapros='PRAGMA table_info ({0})'.format(table_name)
        res=[]
        [res.append([x[1],x[2]]) for x in self._execute(zapros)]
        return res
    #
    def create_table(self,table_name,fld_type):
        '''Создание таблицы
        table_name=None - имя таблицы
        fld_type Словарь с именами и типами полей таблицы'''
        #
        newtbl=False
        if isinstance(fld_type,dict):#and (not self.exists_tables(table_name))
            fld=['"{0}" {1}'.format(f,t)  for f,t in fld_type.items()]
            zapros='CREATE TABLE "{0}"({1})'.format(table_name,','.join(fld))
            self._execute(zapros)
        return self.get_table(table_name)
        #
    def delete_table(self,table_name):
        '''Удаление таблицы
        table_name=None - имя таблицы'''
        #
        res=False
        if self.exists_tables(table_name):
            zapros='DROP TABLE "{0}"'.format(table_name)
            if self._execute(zapros,())!=False:
                self.__log.add('delete','Удалена таблица: {0}'.format(table_name),zapros)
                res=True
        else:
            self.log.add('delete','Таблица: {0} не существует'.format(table_name),zapros)
        return res
#
#
#
class tables(set_info):
    '''Работа с таблицей из БД'''
    #
    def __init__(self,dbname=None,path=None,table_name=None,fldnametype=None,log=True):
        #БД по умолчанию
        set_info.__init__(self,dbname,path)
        #Начальные значения переменных
        #Имя текущей таблицы
        self.__table_name=table_name
        #
        self.__fldnametype=fldnametype
        #
        self.__fldname=[x[0] for x in self.__fldnametype]
    #
    def insert(self,fld_nm_val):
        '''Вставка в таблицу
        fld_nm_val-словарь {'param_name': param_value}'''
        #
        #Компоновка запроса
        table_name=self.__table_name
        #
        res=False
        if self.__table_name:
            fld_nm_val=self._validate_filds_name(fld_nm_val)
            #
            if fld_nm_val!=False:
                param,fld=[],[]
                for f,v in fld_nm_val.items():
                    param.append(v)
                    fld.append(f)
                param=tuple(param)
                #
                zapros='INSERT INTO {0} ({1}) VALUES ({2})'.format(self.__table_name,','.join(fld),','.join(["?"]*len(fld_nm_val)))
                res=self._execute(zapros,param)
                res=not self.error
        return res
    #
    def select(self,where='1=1',filds='*'):
        '''Выборка из таблицы
        where='1=1' - условие
        filds='*' - список полей []'''
        #
        res=False
        if self.__table_name:
            filds=self._validate_filds_name(filds)
            if isinstance(filds,list):
                filds=','.join(filds)
            elif filds==False:
                filds='*'
            #
            zapros='SELECT {0} FROM {1} WHERE {2}'.format(filds,self.__table_name,where)
            #
            res=self._execute(zapros)
        self.log.add('select',res,zapros)
        return res
    #
    def update(self,fld_nm_val,where):
        '''Обновление записи
        where - условие
        fld_nm_val-словарь {'param_name': param_value}
        table_name=self.__table_name'''
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
                fld=','.join(fld)
                #
                zapros='UPDATE {0} SET {1} WHERE {2}'.format(table_name,fld,where)
                #
                self._execute(zapros,param)
                res=not self.error
        return res
    #
    def delete(self,where):
        '''Удаление записи
        where - условие'''
        #
        res=False
        if self.__table_name:
            zapros='DELETE from {0} WHERE {1}'.format(self.__table_name,where)
            res=self._execute(zapros)
            #
        return res
    #
    def count(self):
        '''Количество записей в текущей таблице'''
        #
        res=self.select()
        if res:
            return len(res)
        else:
            return 0
    #
    def _validate_filds_name(self,filds):
        '''проверка имени поля
        filds - словарь {fild_name:fild_value} или список имен полей'''
        #
        #если проверяется словарь
        if isinstance(filds,dict):
            del_fld=[fld for fld in filds.keys() if not(fld in self.__fldname)]
            for fld in del_fld:
                del filds[fld]
            if len(filds)==0: filds=False
        #Если проверяется список
        elif isinstance(filds,list):
            filds=[fld for fld in filds if fld in self.__fldname]
            if len(filds)==0: filds=False
        #если проверяется строка
        elif isinstance(filds,str):
            if not(filds in self.__fldname): filds=False
        else: filds=False
        #возврат словаря/списка/строки соответствующих полям в таблице
        return filds
    #
    def _validate_filds_value(self,fld_name,fld_value):
        '''Проверка fld_name записи
        fld_name - имя поля
        fld_value - значение'''
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
    def max_fld(self,fld):
        '''Максимальное значение столбца'''
        #
        zapros='SELECT MAX({0}) FROM "{1}"'.format(fld,self.__table_name)
        res=self._execute(zapros)
        if not self.error:
            max_res=res[0][0]
        else:
            max_res=False
        return max_res
    #
    #
    #
def main():
    info()
if __name__ == '__main__':
    main()
    #
