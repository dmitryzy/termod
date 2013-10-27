# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         CHEMCAD TERMOD термодинамические расчеты
# Purpose:      Компоненты для термодинамических расчетов
#               связанных с веществом, реакцией и системой из нескольких веществ.
#               Содержит классы subst, reaktion, chem_system, chem_table, chem_parametr, temperature, area, volume, pressure.
#
# Author:       Цымай Дмитрий
#
# Created:      24.06.2013
# Copyright:    (c) Цымай Дмитрий 2013
# Licence:      LGPL
#-------------------------------------------------------------------------------
#!/usr/bin/env python
#
import string
import os
import db_sqlite_py as db
import sys
import numpy as np
#
R_constant=8.31
#Число знаков после запятой для округления
round_digit=3
#список фазовых состояний
lst_phase=['g','k','l','s']

class subst(object):
    '''Класс subst предназначен для выполнения расчетов связанных с химическим
    веществом, идентифицируемом по формуле
    содержит методы определения элементного состава,
    расчета молекулярной массы
    расчета термодинамических характеристик'''
    #
    def __init__(self,formula,phase,newparametr,newtable):
        '''Химическое вещество
        formula - Формула (строка)
        phase - Фазовое состояние (строка "g","k","l","s")
        newparametr - Словарь, содержащий ссылки на параметры состояния
        newdatabase - Словарь, содержащий ссылки на таблицы базы данных'''
        #
        #Список полей базы данных, используемой в расчетах
        self.__lst_filds=["subst","dt1","dt2","dh298","da","db","dc","dd","ds298","uat0","m_coeff","n_coeff","dhh298","dhfp","z_coeff","phase"]
        #Установка параметров БД
        self.set_database(newtable)
        #Получение названий полей
        self.get_fld_name()
        #
        #Список фазовых состояний
        self.__lst_phase=lst_phase
        #Фазовое состояние
        self.set_phase(phase)
        #Формула
        self.__formula=formula
        #Получение информации о веществе
        self.get_termod_info()
        #Установка параметров
        self.__parametr={}
        self.set_parametr(newparametr)
        #Получение элементной матрицы
        self.__treematrix=to_substmatrix(self.__formula,2)
        self.__substmatrix=to_substmatrix(self.__formula)
        #Свойства
        #Коэффициент (по умолчанию 1)
        self.st_koeff=1
        #Мольная доля (по умолчанию 1)
        self.moll_konz=1
        #Количество вещества
        self.moll=0
        #Масса вещества
        self.massa=0
    #
    def set_database(self,dict_tbl):
        '''Метод устанавливает  ссылки на таблицы
        с термодинамической информацией и проверяет их структуру
        dict_tbl - Словарь, содержащий ссылки на таблицы
        Формат словаря:
        {'term-base':<tables>,'term-name-fld':<tables>,'term-ellingem':<tables>,
        'term-ellingem-name':<tables>}
        Значения словаря по умолчанию: None'''
        #
        self.DataTable={}.fromkeys(['term-base','term-name-fld','term-ellingem''term-ellingem-name'])
        if isinstance(dict_tbl,dict):
            new_dict_tbl={k:v for k,v in dict_tbl.items() if isinstance(v,db.tables)}
            self.DataTable={k:v for k,v in new_dict_tbl.items() if k in self.DataTable}
            #
    #
    def set_parametr(self,dict_param=None):
        '''Метод устанавливает значения параметров состояния
        Если они не заданы, то устанавливает стандартные значения
        dict_param - Словарь, ключами которого являются наименования параметров,
         а значениями соответствующие объекты'''
        #
        self.__parametr['temperature']=temperature(298)
        self.__parametr['pressure']=pressure(100000)
        #
        if isinstance(dict_param,dict):
            if 'temperature' in dict_param:
                if isinstance(dict_param['temperature'],temperature):
                    self.__parametr['temperature']=dict_param['temperature']
                    self.__parametr['temperature'].set_units('K')
            if 'pressure' in dict_param:
                if isinstance(dict_param['pressure'],pressure):
                    self.__parametr['pressure']=dict_param['pressure']
    #
    def get_parametr(self):
        '''Метод возвращает словарь с установленными параметрами системы'''
        #
        return self.__parametr
    #
    def get_subst_db_names(self):
        '''Метод возвращает список веществ имеющихся в базе данных
        Формат возвращаемых данных: список'''
        #
        subst_db_names=set()
        subst_db_names.update([x[0] for x in self.DataTable['term-base'].select('1=1','subst')])
        return subst_db_names
    #
    def is_valid_subst(self):
        '''Метод проверяет наличие вещества, заданного формулой в базе данных
        Возвращает логическое значение True или False'''
        if self.__formula in self.get_subst_db_names():
            return True
        else:
            return False
    #
    def get_termod_info(self):
        '''Метод запрашивает информацию о веществе из базы данных
        Выполняется проверка наличия информации о веществе в базе данных
        Формат возвращаемых данных: список словарей'''
        #
        if self.is_valid_subst():
            res=self.DataTable['term-base'].select('subst="{0}"'.format(self.__formula),self.__lst_filds)
            self.__subst_termod_data=[{k:v for k,v in zip(self.__lst_filds,t_res)} for t_res in res]
        else: self.__subst_termod_data=False
        return self.__subst_termod_data
    #
    def get_fld_name(self):
        '''Метод запрашивает названия полей, хранимых в базе данных (основная таблица таблица термодинамических свойств)
        Формат возвращаемых данных: словарь {<имя поля в таблице>:<полное название поля>}'''
        #
        if self.DataTable['term-name-fld']:
            fld_nm=self.DataTable['term-name-fld'].select(filds=['fld_name','fld_full_name'])
        else:
            fld_nm=[[x,x] for x in self.__lst_filds]
        #
        self.__lst_filds_name={x[0]:x[1] for x in fld_nm}
        return self.__lst_filds_name
    #
    def get_subst_matrix(self):
        '''Метод возвращает матрицу элементного состава вещества
        Формат возвращаемых данных: словарь {<символ элемента>:<индекс>}'''
        #
        return self.__substmatrix
    #
    def print_subst_info(self):
        '''Метод выводит на печать информации о веществе'''
        #
        out=[]
        if self.__subst_termod_data:
            out.append('Табличные данные о веществе {0} '.format(self.__formula))
            i=0
            for subst_t_info in self.__subst_termod_data:
                out.append('Температурный интервал: от {0} \t до {1} К '.format(subst_t_info['dt1'],subst_t_info['dt2']))
                out.append('Основные параметры ')
                if i==0:
                    out.append('{0}: \t {1}'.format(self.__lst_filds_name['dh298'],subst_t_info['dh298']))
                    out.append('{0}: \t {1}'.format(self.__lst_filds_name['ds298'],subst_t_info['ds298']))
                    out.append('{0}: \t {1}'.format(self.__lst_filds_name['dhh298'],subst_t_info['dhh298']))
                    out.append('{0}: \t {1}'.format(self.__lst_filds_name['uat0'],subst_t_info['uat0']))
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['dhfp'],subst_t_info['dhfp']))
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['phase'],subst_t_info['phase']))
                if i==0:
                    out.append('Структура')
                    out.append('{0}: \t {1} '.format(self.__lst_filds_name['m_coeff'],subst_t_info['m_coeff']))
                    out.append('{0}: \t {1} '.format(self.__lst_filds_name['n_coeff'],subst_t_info['n_coeff']))
                    out.append('{0}: \t {1} '.format(self.__lst_filds_name['z_coeff'],subst_t_info['z_coeff']))
                    #
                out.append('теплоемкость (коэффициенты полинома)')
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['da'],subst_t_info['da']))
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['db'],subst_t_info['db']))
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['dc'],subst_t_info['dc']))
                out.append('{0}: \t {1} '.format(self.__lst_filds_name['dd'],subst_t_info['dd']))
                i+=1
        else:
            out.append('Вещество {0} отсутствует в базе данных'.format(self.__formula))
        print('\n'.join(out))
    #
    def Cp_t(self):
        '''Метод возвращает поправку для теплоемкости вещества в зависимости от изменения температуры
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #цикл по температурным интервалам
        if self.__subst_termod_data:
            #
            j=0
            for t in temperatur:
                #Проверка значения > нижней границы первого температурного интервала
                if t<=self.__subst_termod_data[0]["dt1"]: t=self.__subst_termod_data[0]["dt1"]
                #
                res_t=0
                for subst_t_data in self.__subst_termod_data:
                    if t>=subst_t_data["dt2"]:
                        #Расчет теплоемкости
                        #Для предшествующих температурных интервалов
                        res_t+=subst_t_data["da"]
                        res_t+=subst_t_data["db"]*subst_t_data["dt2"]/1000.0
                        res_t+=subst_t_data["dc"]*(subst_t_data["dt2"]**2)/1000000.0
                        res_t-=subst_t_data["dd"]*(subst_t_data["dt2"]**(-2))*100000.0
                    elif (t<subst_t_data["dt2"])and(t>=subst_t_data["dt1"]):
                        #Расчет для данной температуры в данном интервале
                        #
                        res_t+=subst_t_data["da"]
                        res_t+=subst_t_data["db"]*t/1000.0
                        res_t+=subst_t_data["dc"]*(t**2)/1000000.0
                        res_t-=subst_t_data["dd"]*(t**(-2))*100000.0
                #Запись результата для данной температуры в массив
                res[j]=res_t
                j+=1
        #пересчет из Дж в кДж
        return np.around(res*self.st_koeff/1000.0,round_digit)
    #
    def delta_Int_S_Cp_t(self):
        '''Метод возвращает поправку для теплоемкости вещества в зависимости от изменения температуры
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #цикл по температурным интервалам
        if self.__subst_termod_data:
            #
            j=0
            for t in temperatur:
                #Проверка значения > нижней границы первого температурного интервала
                if t<=self.__subst_termod_data[0]["dt1"]: t=self.__subst_termod_data[0]["dt1"]
                #
                res_t=0
                for subst_t_data in self.__subst_termod_data:
                    if t>=subst_t_data["dt2"]:
                        #Расчет поправки
                        #Для предшествующих температурных интервалов
                        res_t+=subst_t_data["da"]*np.log(subst_t_data["dt2"]/subst_t_data["dt1"])
                        res_t+=subst_t_data["db"]*(subst_t_data["dt2"]-subst_t_data["dt1"])/1000.0
                        res_t+=subst_t_data["dc"]*(subst_t_data["dt2"]**2-subst_t_data["dt1"]**2)/2000000.0
                        res_t-=subst_t_data["dd"]*(subst_t_data["dt2"]**(-2)-subst_t_data["dt1"]**(-2))*100000.0/3
                        res_t+=subst_t_data["dhfp"]*1000.0/subst_t_data["dt2"]
                    elif (t<subst_t_data["dt2"])and(t>=subst_t_data["dt1"]):
                        #Расчет для данной температуры в данном интервале
                        #
                        res_t+=subst_t_data["da"]*np.log(t/subst_t_data["dt1"])
                        res_t+=subst_t_data["db"]*(t-subst_t_data["dt1"])/1000.0
                        res_t+=subst_t_data["dc"]*(t**2-subst_t_data["dt1"]**2)/2000000.0
                        res_t-=subst_t_data["dd"]*(t**(-2)-subst_t_data["dt1"]**(-2))*100000.0/3
                #Запись результата для данной температуры в массив
                res[j]=res_t
                j+=1
        #пересчет из Дж в кДж
        return np.around(res*self.st_koeff/1000.0,round_digit)
    #
    def delta_Int_Cp_t(self,fp=False):
        '''Метод возвращает поправку для теплоемкости вещества в зависимости от изменения температуры
        Формат возвращаемых данных: массив вещественных чисел
        Параметры:
        fp=False учитывать/не учитывать фазовые переходы (True/False)'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #цикл по температурным интервалам
        if self.__subst_termod_data:
            #
            j=0
            for t in temperatur:
                #Проверка значения > нижней границы первого температурного интервала
                if t<=self.__subst_termod_data[0]["dt1"]: t=self.__subst_termod_data[0]["dt1"]
                #
                res_t=0
                for subst_t_data in self.__subst_termod_data:
                    if t>=subst_t_data["dt2"]:
                        #Расчет поправки
                        #Для предшествующих температурных интервалов
                        res_t+=subst_t_data["da"]*(subst_t_data["dt2"]-subst_t_data["dt1"])
                        res_t+=subst_t_data["db"]*(subst_t_data["dt2"]**2-subst_t_data["dt1"]**2)/2000.0
                        res_t+=subst_t_data["dc"]*(subst_t_data["dt2"]**3-subst_t_data["dt1"]**3)/3000000.0
                        res_t-=subst_t_data["dd"]*(subst_t_data["dt2"]**(-1)-subst_t_data["dt1"]**(-1))*100000.0
                        if fp!=True:
                            res_t+=subst_t_data["dhfp"]*1000.0
                    elif (t<subst_t_data["dt2"])and(t>=subst_t_data["dt1"]):
                        #Расчет для данной температуры в данном интервале
                        #
                        res_t+=subst_t_data["da"]*(t-subst_t_data["dt1"])
                        res_t+=subst_t_data["db"]*(t**2-subst_t_data["dt1"]**2)/2000.0
                        res_t+=subst_t_data["dc"]*(t**3-subst_t_data["dt1"]**3)/3000000.0
                        res_t-=subst_t_data["dd"]*(t**(-1)-subst_t_data["dt1"]**(-1))*100000.0
                #Запись результата для данной температуры в массив
                res[j]=res_t
                j+=1
        #пересчет из Дж в кДж
        return np.around(res*self.st_koeff/1000.0,round_digit)
    #
    def entalp(self):
        '''Энтальпия образования вещества при заданной температуре
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #
        if self.__subst_termod_data:
            res+=self.__subst_termod_data[0]["dh298"]+self.delta_Int_Cp_t()
        return np.around(res*self.st_koeff,round_digit)
    #
    def entrop(self):
        '''Энтропия образования вещества при заданной температуре
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        #
        res=np.zeros(self.__parametr['temperature'].get_size())
        if self.__subst_termod_data:
            res+=self.__subst_termod_data[0]["ds298"]/1000+self.delta_Int_S_Cp_t()
        return np.around(res*self.st_koeff,round_digit)
    #
    def gibbs(self):
        '''Энергия Гиббса образования вещества при заданной температуре
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        temperatur=self.__parametr['temperature'].get_value()
        #
        res=np.zeros(self.__parametr['temperature'].get_size())
        if self.__subst_termod_data:
            res+=self.entalp()-temperatur*self.entrop()
        return np.around(res*self.st_koeff,round_digit)
    #
    def gelmgolz(self):
        '''Энергия Гельмгольца образования вещества при заданной температуре
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        global R_constant
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        res+=self.gibbs()
        #
        if self.__phase=='g':
            res+=R_constant*temperatur*self.moll
        return np.around(res,round_digit)
    #
    def u_atomize(self,coord):
        '''Энергия атомизации вещества
        Формат возвращаемых данных: массив вещественных чисел
        coord - параметр, определяющий:
        расчитывать энергию, приходящуюся на одну связь (coord=True)
        или полную энергию (coord=False)'''
        #
        global round_digit
        global R_constant
        #
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #
        if self.__subst_termod_data:
            res+=self.__subst_termod_data[0]["uat0"]
            res-=temperatur*(3*(self.__subst_termod_data[0]["m_coeff"]*2+self.__subst_termod_data[0]["n_coeff"])/2)*R_constant/1000.0
            res-=self.delta_Int_Cp_t(True)
            res=res/self.__subst_termod_data[0]["m_coeff"]
            if coord==True:
                res=res/self.__subst_termod_data[0]["z_coeff"]
        #
        return np.around(res,round_digit)
    #
    def chem_potential(self):
        '''Расчет химического потенциала вещества
        Формат возвращаемых данных: массив вещественных чисел'''
        #
        global round_digit
        global R_constant
        #
        temperatur=self.__parametr['temperature'].get_value()
        res=np.zeros(self.__parametr['temperature'].get_size())
        #
        res+=self.gibbs()+R_constant*temperatur*np.log(self.moll_konz)
        return np.around(res,round_digit)
    #
    def set_phase(self,newphase):
        '''Устанавливает фазовое состояние вещества
        newphase - Новое фазовое состояние (строка 'g','k','l','s')'''
        #
        if newphase in self.__lst_phase:
            self.__phase=newphase
        else:
            self.__phase=self.__lst_phase[0]
        return self.__phase
    #
    def get_phase(self):
        '''Возвращает фазовое состояние'''
        #
        return self.__phase
    #
    def formula(self,prn_format='html'):
        '''Возвращает html представление формулы вещества
        prn_format - параметр, определяющий представление фомулы ('html', 'txt', 'tex')'''
        #
        return to_formula(self.__formula,prn_format)
    #
    def ellingem(self):
        pass
    #
#
#
class reaktion(object):
    '''Класс предназначен для расчетов связанных с химической реакцией
    идентифицируемой по стехиометрической матрице
    содержит методы выполнения стехиометрических расчетов,
    уравнивания коэффициентов, расчета термодинамических характеристик
    для химической реакции'''
    #
    def __init__(self,subst_koeff_phase,newparametr,newtable):
        '''Определение химической реакции
        Параметры:
            subst_koeff_phase список, элементами которого являются кортежи:
            [(формула вещества, стехеометрический коэффициент, фаза), ]
            newtemperatur - интервал температур (объект класса temperature)
            newparametr - Словарь, содержащий ссылки на параметры состояния
            newdatable - Словарь, содержащий ссылки на таблицы базы данных'''
        #Параметры,определяющие правильность задания реакции
        #Существование веществ в базе данных
        self.__validsubst={}
        #правильность уравнивания коэффициентов
        self.__validkoeff=True
        #Список веществ (объектов subst)
        self.__subst_list=[]
        #Стехеометрическая матрица Словарь вида {<формула вещества>:<стехеометрический коэффициент>}
        self.__subst_matrix={}
        #Множество элементов
        self.elems=set()
        #Множество формул
        self.forms=set()
        #Определение веществ
        for els in subst_koeff_phase:
            subst_name,koeff,phase=els
            n_subst=subst(subst_name,phase,newparametr,newtable)
            if n_subst.is_valid_subst():
                n_subst.st_koeff=koeff
                self.__subst_list.append(n_subst)
                self.elems.update(n_subst.get_subst_matrix().keys())
                self.forms.add(n_subst.formula('txt'))
                self.__validsubst[n_subst.formula('txt')]=True
            else:
                self.__validsubst[n_subst.formula('txt')]=False
        #
        self.koeff_calc()
        #
        if len(self.__subst_list)>0:
            #Подключение таблиц БД
            self.DataTable=self.__subst_list[0].DataTable
            #Установка параметров системы
            self.__parametr=self.__subst_list[0].get_parametr()
            #
            #Кинетические параметры
            self.__energy=0 #Энергия активации
            self.__factor=1 #Предэкспоненциальный множитель
            self.__ordnung={}
            self.set_ordnung() #Частные кинетические порядки реакции
    #
    def validate(self):
        '''Проверка правильности задания параметров реакции'''
        #
        for frm,val in self.__validsubst.values():
            if val==True:
                print('Вещество {0} присутствует в базе даных')
            else:
                print('Вещество {0} отсутствует в базе даных')
        #
        if self.__validkoeff:
            print('Коэффициенты реакции уравнены')
        else:
            print('Коэффициенты реакции не уравнены')
    #
    def is_valid(self):
        '''Метод возвращает True, усли все вещества
        указанные в реакции заданы правильно
        и она правильно уравнена.'''
        #
        if (self.__validkoeff==True)and(False not in self.__validsubst.values()):
            return True
        else:
            return False
    #
    def set_parametr(self,dict_param=None):
        '''Изменяет параметры для всех веществ системы.
        Параметры:
            dict_param - Словарь, ключами которого являются наименования параметров,
            а значениями соответствующие объекты'''
        #
        for sbs in self.__subst_list:
            sbs.set_parametr(dict_param)
    #
    def get_matrix(self):
        '''Метод для определения значения стехеометрической матрицы реакции'''
        #
        return self.__subst_matrix
    #
    def entalp(self):
        '''Расчет энтальпии реакции при заданной температуре'''
        #
        return sum([sbs.entalp() for sbs in self.__subst_list])
    #
    def entrop(self):
        '''Расчет энтропии реакции при заданной температуре'''
        #
        return sum([sbs.entrop() for sbs in self.__subst_list])
    #
    def gibbs(self):
        '''Расчет энергии Гиббса реакции при заданной температуре'''
        #
        return sum([sbs.gibbs() for sbs in self.__subst_list])
    #
    def gelmgolz(self):
        '''Расчет энергии Гельмгольца реакции при заданной температуре'''
        #
        return sum([sbs.gelmgolz() for sbs in self.__subst_list])
    #
    def const_p(self):
        '''Расчет константы равновесия реакции при заданной температуре'''
        #
        global round_digit
        global R_constant
        #
        temperatur=self.__parametr['temperature'].get_value()
        res=np.exp(-self.gibbs()*1000/temperatur/R_constant)
        return np.around(res,round_digit)
    #
    def log_const_p(self):
        '''Расчет натурального логарифма константы равновесия реакции при заданной температуре'''
        #
        global round_digit
        global R_constant
        temperatur=self.__parametr['temperature'].get_value()
        #
        res=-self.gibbs()*1000/temperatur/R_constant
        return np.around(res,round_digit)
    #
    def temperatur_nr(self):
        '''Расчет температуры начала реакции
        возвращаемое значение: строка'''
        #
        global round_digit
        old_parametr=self.__parametr.copy()
        #
        self.set_parametr()
        ent298=self.entalp()[0]
        entr298=self.entrop()[0]
        tnr=np.around(ent298/entr298,round_digit)
        self.set_parametr(old_parametr)
        #
        res=None
        #
        if (ent298>0)and(entr298<0):
            res='реакция не может протекать при температуре T>0 K'
        elif (ent298<0)and(entr298>0):
            res='реакция всегда может протекать при температуре T>0 K'
        elif (ent298<0)and(entr298<0):
            res='T<{0} K'.format(tnr)
        elif (ent298>0)and(entr298>0):
            res='T>{0} K'.format(tnr)
        return res
    #
    def print_info(self):
        '''печать основной информации о реакции'''
        #
        str_right=[]
        str_left=[]
        for sbs in self.__subst_list:
            str_koeff=''
            if sbs.st_koeff>0:
                if sbs.st_koeff!=1:
                    str_koeff=str(sbs.st_koeff)
                str_right.append(str_koeff+sbs.formula('txt')+'('+sbs.get_phase()+')')
            else:
                if sbs.st_koeff!=-1:
                    str_koeff=str(-sbs.st_koeff)
                str_left.append(str_koeff+sbs.formula('txt')+'('+sbs.get_phase()+')')
        #
        Q=-self.entalp()[0]
        return '{0} = {1}+{2} кДж ({3})'.format('+'.join(str_left),'+'.join(str_right),Q,self.temperatur_nr())
    #
    def set_reagents(self,form_moll):
        '''Метод устанавливает значения количеств реагентов
        form_moll - Словарь, ключами которого являются формулы веществ,
         а значениями их количества, моль
         {<формула вещества>:<количество вещества, моль>, }'''
        #
        if isinstance(form_moll,dict):
            for sbs in self.__subst_list:
                formula=sbs.formula('txt')
                if formula in form_moll:
                    sbs.moll=form_moll[formula]
    #
    def get_reagents(self):
        '''Метод возвращает количество вещества реагентов, моль'''
        #
        return {sbs.formula('txt'):sbs.moll for sbs in self.__subst_list}
    #
    def degree_max(self):
        '''Метод возвращает максимальное значение степени полноты'''
        #
        return min([-sbs.moll/sbs.st_koeff for sbs in self.__subst_list if sbs.st_koeff<0])
    #
    def degree(self,x):
        '''Метод пересчитывает количества вещества реагентов на величину x
        x - степень полноты реакции'''
        #
        max_x=self.degree_max()
        re_x=x if x<max_x else max_x
        for sbs in self.__subst_list:
            sbs.moll+=sbs.st_koeff*x
        return self.get_reagents()
    #
    def __mul__(self,num):
        '''Умножение реакции на коэфициент
        num - Число, на которое умножаются коэффициенты реакции'''
        #
        if (isinstance(num,int) or isinstance(num,float))and(num!=0):
            for sbs in self.__subst_list:
                sbs.st_koeff*=num
                self.__subst_matrix[sbs.formula('txt')]=sbs.st_koeff
        elif num==0:
            print('error num is non zero')
        return self
    #
    def set_koeff(self,frm_koeff):
        '''Метод устанавливает значения стехеометрических коэффициентов
        для всех веществ, входящих в реакцию.
        Параметры:
            frm_koeff - Словарь, ключами которого являются формулы, а значениями коэффициенты
            {<Формула>:<Стехеометрический коэффициент>}'''
        #
        if isinstance(frm_koeff,dict):
            for sbs in self.__subst_list:
                frm=sbs.formula('txt')
                sbs.st_koeff=frm_koeff[frm] if frm in frm_koeff.keys() else 1
                self.__subst_matrix[frm]=frm_koeff[frm]
    #
    def koeff_calc(self):
        '''Расчет стехеометрических коэффициентов реакции
        Возвращает стехеометрическую матрицу реакции
        словарь вида:
            {<формула вещества>:<стехеометрический коэффициент>,}'''
        #
        k_matr=[]
        for sbs in self.__subst_list:
            el_matr=sbs.get_subst_matrix()
            el_matr.update({el:0 for el in self.elems if el not in el_matr})
            k_matr.append([el_matr[el] for el in self.elems])
        #
        eq_count=len(self.elems)
        sbs_count=len(self.__subst_list)
        eq=min(eq_count,sbs_count)
        b_matrix=np.zeros((eq,1))
        #
        a_matrix=np.array([[row[i] for row in k_matr[:eq]] for i in range(eq_count)])
        if eq<sbs_count:
            b_matrix=np.array([[row] for row in k_matr[-1][:eq_count]])
        else:
            b_matrix=np.zeros((eq,1))
        #
        koeff=np.linalg.solve(a_matrix,b_matrix)
        if eq<sbs_count:
            koeff=np.append(koeff,1)
        #
        frm_koeff={self.__subst_list[i].formula('txt'):koeff[i]*np.sign(self.__subst_list[i].st_koeff) for i in range(sbs_count)}
        self.set_koeff(frm_koeff)
        #
        return self.__subst_matrix
    #
    def rate(self,energy):
        pass
    #
    def kinetik_koeff(self,factor=None,energy=None,log=False):
        '''Метод расчитывает кинетический коэффициент реакции по уравнению Аррениуса.
        Параметры метода:
            energy - энергия активации
            factor - предэкспоненциальный множитель
            log - формат вывода
                log=True логарифм константы
                log=False константа'''
        #
        if energy!=None:
            self.__energy=np.float(energy)
        if factor!=None:
            self.__factor=np.float(factor)
        #
        if log==True:
            res=np.log(self.__factor)-self.__energy/(R_constant*self.__parametr['temperature'].get_value())
        else:
            res=self.__factor*np.exp(-self.__energy/(R_constant*self.__parametr['temperature'].get_value()))
        return res
    #
    def parametr_kinetik(self,kin_konst,temp):
        '''Метод возвращает параметры кинетической константы:
            предэкспоненциальный множитель и энергию активацииив виде кортежа:
                (<предэкспоненциальный множитель>,<энергия активации>).
                Расчет выполняется по уравнению Аррениуса
        Пераметры метода:
            kin_konst - кортеж из двух кинетических констант, при различных температурах <float>
            temp - кортеж из двух значений температуры <float>'''
        #
        energy,factor=0,0
        if (isinstance(kin_konst,tuple))and(isinstance(temp,tuple)):
            if (len(kin_konst)==2)and(len(temp)==2):
                self.__energy=(R_constant*temp[0]*temp[1]/(temp[0]-temp[1]))*np.log(kin_konst[0]/kin_konst[1])
                self.__factor=np.exp((temp[0]*np.log(kin_konst[0])-temp[1]*np.log(kin_konst[1]))/(temp[0]-temp[1]))
            else:
                print('Необходимы кортежи из двух элементов')
        #
        return (self.__factor,self.__energy)
    #
    def zdm(self,course='reversible',prn_format='html',variable='[]',ph='g'):
        '''Метод, возвращающий выражение закона действующих масс для реакции
        Возвращаемое выражение: строка в формате tex или html.
        Параметры метода:
            course - направление реакции.
            Принимает значения:
                course='forward' прямая
                course='reverse' обратная
                course='reversible' обратимая
            prn_format='html' - Формат выводимых данных.
            Принимает значения:
                prn_format='tex' tex
                prn_format='html' html
            variable='[]' - тип переменных для вывода.
            Принимает значения:
                variable='[]' молярные концентрации (старая запись)
                variable='x' мольные доли
                variable='p' парциальные давления
                variable='C' молярные концентрации (новая запись)
            ph='g' - основная фаза. Принимает значения: 'g','k','l','s'.
            (по обозначениям фаз)'''
        #
        mtr={sbs.formula('txt'):sbs.st_koeff for sbs in self.__subst_list if sbs.get_phase()==ph}
        #
        s_v,s_vb,s_ve='','[',']'
        #
        if prn_format=='html':
            s_u,s_b,s_e,s_kb,s_ke='','<sup>','</sup>','<sub>','</sub>'
            #
            if variable!='[]':
                s_v,s_vb,s_ve=str(variable),'<sub>','</sub>'
        elif prn_format=='tex':
            s_u,s_b,s_e,s_kb,s_ke='\cdot ','^{','}','_{','}'
            #
            if variable!='[]':
                s_v,s_vb,s_ve=str(variable),'_{','}'
        #
        res=''
        res1='k{0}+{1}'.format(s_kb,s_ke)+s_u.join(['{4}{5}{0}{6}{1}{2}{3}'.format(to_formula(frm,prn_format),s_b,-ind,s_e,s_v,s_vb,s_ve) for frm,ind in mtr.items() if ind<0])
        res2='k{0}-{1}'.format(s_kb,s_ke)+s_u.join(['{4}{5}{0}{6}{1}{2}{3}'.format(to_formula(frm,prn_format),s_b,ind,s_e,s_v,s_vb,s_ve) for frm,ind in mtr.items() if ind>0])
        if course=='forward':
            res='v={0}'.format(res1)
        elif course=='reverse':
            res='v={0}'.format(res2)
        elif course=='reversible':
            res='v={0}-{1}'.format(res1,res2)
        return res
    #
    def zdm_eval(self,val_degree=0,course='reversible',variable='x',ph='g',par=1):
        '''Метод вычисляет значение скорости по закону действующих масс
        при заданной величине степени полноты рекции val_degree.
        По умолчанию val_degree=0.
        Предварительно должна быть расчитана кинетическая константа при помощи
        одного из методов kinetik_koeff() или parametr_kinetik().
        По умолчанию кинетическая константа равна 1.
        Параметры метода:
            course - направление реакции.
            Принимает значения:
                course='forward' прямая
                course='reverse' обратная
                course='reversible' обратимая
            variable='x' - тип переменных для вывода.
            Принимает значения:
                variable='x' мольные доли
                variable='p' парциальные давления
                (должен быть задан параметр давления)
                variable='C' молярные концентрации
                (должен быть задан параметр объема)
            ph='g' - основная фаза. Принимает значения: 'g','k','l','s'.
            (по обозначениям фаз)
            par=1 - Дополнительный параметр
            (давление или объем в зависимости от значения параметра variable)'''
        #
        k_kin1=self.kinetik_koeff()
        k_kin2=1#k_kin1/self.const_p()
        #
        moll=self.degree(val_degree)
        ordn=self.get_ordnung()
        moll_s=np.sum([x for x in moll.values()])
        #
        if moll_s>0:
            lst_frm1=[sbs.formula('txt') for sbs in self.__subst_list if (sbs.st_koeff<0)and(sbs.get_phase()==ph)]
            lst_frm2=[sbs.formula('txt') for sbs in self.__subst_list if (sbs.st_koeff>0)and(sbs.get_phase()==ph)]
            #
            res1=k_kin1*np.prod([(moll[frm]/moll_s)**np.abs(ordn[frm]) for frm in lst_frm1])
            res2=k_kin2*np.prod([(moll[frm]/moll_s)**np.abs(ordn[frm]) for frm in lst_frm2])
            #
            ordn_s1=np.sum([ordn[frm] for frm in lst_frm1])
            ordn_s2=np.sum([ordn[frm] for frm in lst_frm2])
            #
            if course=='forward':
                res=res1
            elif course=='reverse':
                res=res2
            elif course=='reversible':
                res=res1-res2
            else:
                res=res1
            #
            if (variable=='p')and(ph=='g'):
                res1=res1*(par**ordn_s1)
                res2=res2*(par**ordn_s2)
            elif (variable=='C')and((ph=='s')or(ph=='l')or(ph=='g')):
                res1=res1/((R_constant*self.__parametr['temperature'].get_value())**ordn_s1)
                res2=res2/((R_constant*self.__parametr['temperature'].get_value())**ordn_s2)
            elif (variable=='x')and((ph=='s')or(ph=='l')or(ph=='g')):
                res1=res1/(par**ordn_s1)
                res2=res2/(par**ordn_s2)
        else:
            res=0
        return res
    #
    def set_ordnung(self,frm_val=None):
        '''Метод устанавливает значения частных порядков реакции по реагентам.
        Параметры метода:
            frm_val=None - Порядки реакции.
            Словарь вида: {<формула вещества>:<порядок реакции по веществу>}
            Если значение не задано, то частные порядки реакции по веществам
            определяются стехиометрическими коэффициентами.
            Если концентрация данного вещества не определяет скорость реакции,
            задайте значение порядка по веществу равным 0.'''
        #
        if isinstance(frm_val,dict):
            frm_val1={k:v for k,v in frm_val.items() if (isinstance(v,int)or isinstance(v,float))}
            for sbs in self.__subst_list:
                frm=sbs.formula('txt')
                if frm in frm_val1:
                    self.__ordnung[frm]=frm_val1[frm]
                else:
                    self.__ordnung[frm]=sbs.st_koeff
        else:
            self.__ordnung={sbs.formula('txt'):sbs.st_koeff for sbs in self.__subst_list}
    #
    def get_ordnung(self):
        '''Метод возвращает порядки реакции в формате словаря:
            {<формула вещества>:<порядок реакции по веществу>}
        '''
        #
        return self.__ordnung
    #
    def rawn_calc(self,params):
        '''Расчет равновесной степени полноты реакции при заданной температуре'''
        pass
#
#
class chem_system(object):
    '''Класс chem_system
    Предназначен для выполнения расчетов связанных с химической системой,
    в которой протекают химические реакции и в которую входят химические вещества
    Содержит методы выполнения расчетов связанных с системой'''
    #
    def __init__(self,name,subst_moll_phase,newtemperatur):
        '''subst_moll_phase состав системы
        список кортежей вида
        [(<Название вещества>,<Содержание вещества в молях>,<фазовое состояние вещества>),...]'''
        #
        self.__name=name
        #Список веществ
        self.__subst_list=[]
        #Температура
        self.set_temperatur(newtemperatur)
        #Инертный компонент в системе
        self.__inerts=0.0
        #Определяем состав системы
        for els in subst_moll_phase:
            subst_name=els[0]
            moll=els[1]
            phase=els[2]
            #Добавляем новое вещество
            self.add_subst(subst_name,moll,phase)
        #
        #
        #reakts стехеометрические матрицы реакций входящих в состав системы
        #список словарей вида: [{<Название вещества>:<Стехеометрический коэффициент вещества>,...},...]
    #
    def get_info(self):
        form_subst=map(lambda sb:sb.formula,self.__subst_list)
        return [self.__name,form_subst]
    def set_temperatur(self,value):
        if isinstance(value,temperature):
            self.__temperatur=value
        else:
            self.__temperatur=temperature(298)
        #Устанавливаем температуру для всех веществ
        for sbs in self.__subst_list:
            sbs.set_temperatur(self.__temperatur)
    #
    def is_valid_system(self):
        #Метод для проверки параметров системы
        #Проверяет наличие в базе данных информации о веществах
        #входящих в состав системы
        #
        #Проверка равенства суммы мольных долей компонентов системы 100%
        res=True
        res_sum=0.0
        for sbs in self.__subst_list:
            if not sbs.is_valid_subst():
                res=False
            res_sum+=sbs.moll_konz
        res_sum=round(res_sum,2)
        if res_sum==1.0 and res==True:
            return True
        else:
            return False
    #
    def add_subst(self,formula,moll,phase):
        #Метод добавляет новое вещество в систему
        #formula - Формула нового вещества
        #
        #Возвращает True или False
        #
        n_subst=subst(formula,phase,self.__temperatur)
        if n_subst.is_valid_subst()and(moll>0):
            n_subst.moll=moll
            #Добавляем
            self.__subst_list.append(n_subst)
            #Пересчитываем состав
            self.get_sostav()
            #
            return True
        #
        else:
            return False
    #
    def change_all(self,delta_moll):
        #Метод изменяет количество инертного вещества в системе
        #delta_moll - изменение количества вещества в молях
        #units - единицы измерения
        if(delta_moll+self.__inerts>0):
            self.__inerts+=delta_moll
        #
        self.get_sostav()
    #
    def change_subst(self,formula,moll):
        #Метод изменяет количество вещества в системе
        #formula - Формула вещества
        #
        #Возвращает True или False
        #
        try:
            my_num=map(lambda sbs:sbs.formula,self.__subst_list).index(formula)
        except:
            my_num=False
        #
        if(my_num!=False)and(moll>0):
            self.__subst_list[my_num].moll=moll
            #Пересчитываем состав
            self.get_sostav()
            #
            return True
        else:
            return False
    #
    def del_subst(self,formula):
        #Удаляет выбранное вещество из системы, если оно в ней присутствует
        #
        # formula - формула удаляемого вещества
        #
        try:
            del_num=map(lambda sbs:sbs.formula,self.__subst_list).index(formula)
        except:
            del_num=False
        #при наличии вещества в системе удаляем
        if del_num:
            del self.__subst_list[del_num]
            #Пересчитываем состав
            self.get_sostav()
            #
            return True
        #
        else:
            return False
    #
    def get_sostav(self):
        #Метод для определения состава системы
        #Суммарное количество вещества
        self.__all_moll=np.sum(map(lambda sbs:sbs.moll,self.__subst_list))+self.__inerts
        #
        for sbs in self.__subst_list:
            sbs.moll_konz=sbs.moll*100/self.__all_moll
    #
    def u_midl_atomize(self):
        #Средняя энергия атомизации системы
        # при температуре temperatur
        #
        global round_digit
        #
        res=np.zeros(self.__temperatur.get_size())
        #
        for sbs in self.__subst_list:
            res+=sbs.u_atomize(True)*sbs.moll_konz/100
        return np.around(res,round_digit)
    #
    def Kn(self):
        #Коэффициент прочности системы
        #
        global round_digit
        #
        temp=subst('SiO2','k',self.__temperatur)
        temp.set_temperatur(self.__temperatur)
        return np.around(self.u_midl_atomize()/temp.u_atomize(True),round_digit)
    #
    def entalp(self):
        #Метод определяет энтальпию системы
        global round_digit
        #
        res=np.zeros(self.__temperatur.get_size())
        #
        for sbs in self.__subst_list:
            res+=sbs.entalp()*sbs.moll
        return np.around(res,round_digit)
    #
    def entrop(self):
        #Метод определяет энтропию системы
        global round_digit
        #
        res=np.zeros(self.__temperatur.get_size())
        #
        for sbs in self.__subst_list:
            res+=sbs.entrop()*sbs.moll
        return np.around(res,round_digit)
    #
    def gibbs(self):
        #Метод определяет энергию Гиббса системы
        global round_digit
        #
        res=np.zeros(self.__temperatur.get_size())
        #
        for sbs in self.__subst_list:
            res+=sbs.chem_potential()*sbs.moll
        return np.around(res,round_digit)
    #
    def print_system_info(self,units='prozent'):
        #Выводит информацию о составе системы
        #Результат вывода - словарь {<формула вещества>:<количество вещества (в абсолютных или относительных единицах)>}
        #
        global round_digit
        res={}
        if units=='moll':
            for sbs in self.__subst_list:
                res[sbs.formula]=round(sbs.moll,round_digit)
            res['inerts']=round(self.__inerts,round_digit)
            res['itogo']=round(self.__all_moll,round_digit)
            res['units']='moll'
        elif units=='prozent':
            for sbs in self.__subst_list:
                res[sbs.formula]=round(sbs.moll_konz,round_digit)
            res['inerts']=round(self.__inerts*100/self.__all_moll,round_digit)
            res['itogo']=100
            res['units']='%'
        #
        return res
#
class chemstring(object):
    '''Класс объединяет методы обработки и синтаксического анализа строк
     для последующего применения при создании химических объектов'''
    #
    def __init__(self):
        print('f')

#
class chem_table(object):
    def __init__(self,tbl=None):
        '''Метод создает объект таблицы
        '''
        #
        self.__fldname={}
        self.__filds=[]
        self.set_database(tbl)
    #
    def set_database(self,dict_tbl=None):
        '''Метод устанавливает  ссылки на таблицы
        с информацией об элементах и проверяет их структуру
        Параметры:
            dict_tbl - Словарь, содержащий ссылки на таблицы
            Формат словаря: {'mend-table':<tables>}
        Значения словаря по умолчанию: None'''
        #
        self.DataTable={}.fromkeys(['mend-table'])
        if isinstance(dict_tbl,dict):
            new_dict_tbl={k:v for k,v in dict_tbl.items() if isinstance(v,db.tables)}
            self.DataTable={k:v for k,v in new_dict_tbl.items() if k in self.DataTable}
            #
            self.__fldname['num']='номер'
            self.__fldname['name']='Название'
            self.__fldname['smb']='Символ'
            self.__fldname['latname']='Латинское название'
            self.__fldname['period']='Период'
            self.__fldname['grp']='Группа'
            self.__fldname['mass']='Атомная масса(г/моль)'
            self.__fldname['ro']='Плотность,г/см (при 20 град C)'
            self.__fldname['tpl']='Температура плавления ( град C)'
            self.__fldname['tkip']='Температура кипения (град C)'
            self.__fldname['year']='Год открытия'
            self.__fldname['fml']='Первооткрыватель'
            self.__fldname['name1']='Произношение'
            self.__fldname['coment']='Коментарий'
            #
            self.__filds=list(self.__fldname.keys())
            #
    #
    def get_elementlist(self):
        '''Метод возвращает множество символов элементов'''
        return {x[0] for x in self.DataTable['mend-table'].select('1=1','smb')}
    #
    def get_numlist(self):
        '''Метод возвращает множество номеров элементов'''
        return {x[0] for x in self.DataTable['mend-table'].select('1=1','num')}
    #
    def iselement(self,smb):
        '''Возвращает True, если значение smb соответствует химическому элементу.
        Параметры:
            smb - символ (номер) элемента'''
        #
        return True if(smb in self.get_elementlist())or(smb in self.get_numlist()) else False
    #
    def get_attrinfo(self):
        '''Метод возвращает словарь атрибутов элемента
        Формат возвращаемых данных:
            {<поле>:<имя атрибута>,}'''
        #
        return self.__fldname
    #
    def get_fldlist(self):
        '''Метод возвращает список полей таблицы свойств элементов'''
        #
        return self.__filds
    #
    def get_period(self,period):
        '''Возвращает список элементов периода.
        Параметры:
            period - номер периода'''
        #
        res=self.DataTable['mend-table'].select('period={0}'.format(period),['num','smb'])
        if res:
            res=[x[1] for x in sorted(res,key=lambda x: x[0])]
        else:
            res=None
        return  res
    #
    def get_group(self,grp):
        '''Метод возвращает список элементов группы.
        Параметры:
            grp - номер группы'''
        #
        res=self.DataTable['mend-table'].select('grp={0}'.format(grp),['num','smb'])
        if res:
            res=[x[1] for x in sorted(res,key=lambda x: x[0])]
        return  res
    #
    def get_attrvalue(self,elem=None,attr=None):
        '''Метод возвращает значение атрибута элемента.
         Параметры:
            elem - символ (номер) элемента
            attr - аттрибут
            Список значений:
                num - номер
                name - Название
                smb - Символ
                latname - Латинское название
                period - Период
                grp - Группа
                mass - Атомная масса(г/моль)
                ro - Плотность,г/см (при 20 град C)
                tpl - Температура плавления ( град C)
                tkip - Температура кипения (град C)
                year - Год открытия
                fml - Первооткрыватель
                name1 - Произношение
                coment - Коментарий
        '''
        #
        if((attr in self.__filds)and(self.iselement(elem))):
            fld='smb' if isinstance(elem,str) else 'num'
            q=self.DataTable['mend-table'].select('{0}="{1}"'.format(fld,elem),[attr])
            res=q[0][0]
        else:
            res=None
        return res
    #
    def get_element(self,elem,lstattr='*'):
        '''Метод позволяет получить информацию об элементе
         по его символу или номеру. Возвращает словарь вида:
            {<атрибут>:<значение>,}
         Параметры:
            elem - символ (номер) элемента
            lstattr - аттрибуты, которые необходимы (по умолчанию выдаются все)
            Список атрибутов:
                num - номер
                name - Название
                smb - Символ
                latname - Латинское название
                period - Период
                grp - Группа
                mass - Атомная масса(г/моль)
                ro - Плотность,г/см (при 20 град C)
                tpl - Температура плавления ( град C)
                tkip - Температура кипения (град C)
                year - Год открытия
                fml - Первооткрыватель
                name1 - Произношение
                coment - Коментарий
            '''
        #
        if isinstance(lstattr,list):
            lst=[attr for attr in lstattr if attr in self.__filds]
            if len(lst)==0:
                lst=self.__filds
        else:
            lst=self.__filds
        #
        if self.iselement(elem):
            fld='smb' if isinstance(elem,str) else 'num'
            q=self.DataTable['mend-table'].select('{0}="{1}"'.format(fld,elem),lst)
            res={self.__fldname[k]:v for k,v in zip(lst,q[0])}
        else:
            res=None
        return res
    #
    def get_table(self):
        '''Метод возвращает структуру таблицы Менделеева.
        Список списков вида:
            [[{элемент 1},...<элементы 1-го периода>],
             [{элемент 1},...<элементы 2-го периода>],
            ...
             [{элемент 1},...<элементы 7-го периода>]]
        '''
        #
        res=[]
        p=1
        period=self.get_period(p)
        while period!=None:
            res.append(period)
            p+=1
            period=self.get_period(p)
        return res
    #
    def get_attrtable(self,attr):
        '''Метод возвращает таблицу одного из свойств для всех веществ.
        Список списков вида:
            {<элемент>:<значение свойства>,}
        Параметры:
            attr - свойства, которые необходимы (по умолчанию выдаются все)
            Список атрибутов:
                mass - Атомная масса(г/моль)
                ro - Плотность,г/см (при 20 град C)
                tpl - Температура плавления ( град C)
                tkip - Температура кипения (град C)
        '''
        if attr in self.__filds:
             res={x[0]:x[1] for x in self.DataTable['mend-table'].select('1=1',['smb',attr])}
        else:
            res={}
        return res
    #

    def molar_mass(self,el_matrix):
        '''Метод возвращает молярную массу комбинации элементов.
        Параметры:
            el_matrix - элементная матрица. Словарь вида:
                {<Символ элемента>:<индекс>, }
        '''
        #
        if isinstance(el_matrix,dict):
            lst=1
            new_matrix={k:v for k,v in el_matrix.items() if((self.iselement(k))and((isinstance(v,int))or(isinstance(v,float))))}
        if len(new_matrix)>0:
            res=np.sum([self.get_attrvalue(k,'mass')*v for k,v in new_matrix.items()])
        return res
    #
    def molar_volume(self,elem):
        '''Метод возвращает молярный объем элемннта
        Параметры:
            elem - символ или номер элемента'''
        #
        res=None
        if self.iselement(elem):
            ro,mass=self.get_attrvalue(elem,'ro'),self.get_attrvalue(elem,'mass')
            if(ro>0)and(ro!=None):
                res=mass/ro
        return res
    #
#
#
#
class chem_parametr(object):
    '''Класс хранит информацию связанную с параметром
    (температура, давление, объем, площадь)
    В самом общем случае объект класса представляет интервал значений
     с заданными единицами измерения'''
    #
    def __init__(self,name,units,value=None,standart_value=None):
        self.__name=name
        self.__units=units
        self.__lstunits=[]
        self.__standartvalue=standart_value
        self.set_value(value)
    #
    def get_value(self):
        '''Набор значений параметра'''
        #
        return self.__value
    #
    def get_name(self):
        '''Название параметра'''
        #
        return self.__name
    #
    def set_lstunits(self,newlist):
        '''Метод устанавливает список значений параметра'''
        #
        if isinstance(newlist,list):
            self.__lstunits=newlist
    #
    def get_lstunits(self):
        '''Метод возвращает список значений параметра'''
        #
        return self.__lstunits
    #
    def get_units(self):
        '''Единица измерения'''
        #
        return self.__units
    #
    def set_units(self,newunits):
        '''Установить новую единицу измерения'''
        #
        old=self.get_units()
        if (old!=newunits)and(newunits in self.get_lstunits()):
            self.__units=newunits
    #
    def get_parametr(self):
        '''Основные характеристики области определения параметра'''
        #
        return {'min':self.__minvalue,'max':self.__maxvalue,'step':self.__stepvalue,'standart_value':self.__standartvalue}
    #
    def set_value(self,value):
        '''Установка значения параметра'''
        #
        if isinstance(value,list):
            self.__minvalue=value[0]
            self.__maxvalue=value[1]
            self.__stepvalue=value[2]
            self.__value=np.arange(self.__minvalue,self.__maxvalue,self.__stepvalue,float)
        elif(isinstance(value,int))or(isinstance(value,float)):
            self.__minvalue=value
            self.__maxvalue=value
            self.__stepvalue=0
            self.__value=np.array([value],float)
        elif isinstance(value,np.ndarray):
            self.__stepvalue=1
            self.__value=np.array(value,float)
            self.__minvalue=np.min(self.__value)
            self.__maxvalue=np.max(self.__value)
        else:
            self.__minvalue=0
            self.__maxvalue=0
            self.__stepvalue=0
            self.__value=np.zeros(1)
    #
    def get_info(self):
        '''Общая информация о параметре'''
        #
        return {'name':self.__name,'units':self.__units,'value':self.__value,'standart_value':self.__standartvalue}
    #
    def get_size(self):
        '''Количество значений в интервале'''
        #
        return np.size(self.__value)
    #
    def add_value(self,add=0):
        '''Добавить к значениям параметра число'''
        #
        self.__value+=add
        self.__standartvalue+=add
        self.__minvalue=self.__value[0]
        self.__maxvalue=self.__value[-1]

        self.__stepvalue=(self.__maxvalue-self.__minvalue)/(np.size(self.__value)-1)
        return self.__value
    #
    def mul_value(self,mul):
        '''Умножить значение на одно число'''
        #
        self.__value=self.__value*mul
        self.__standartvalue*=mul
        self.__minvalue=self.__value[0]
        self.__maxvalue=self.__value[-1]
        self.__stepvalue=(self.__maxvalue-self.__minvalue)/(np.size(self.__value)-1)
    #
#,temperature, pressure, volume, area
class temperature(chem_parametr):
    '''Параметр температура'''
    #
    def __init__(self,value):
        chem_parametr.__init__(self,'temperatur','K',value,298)
        self.set_lstunits(['K','C','F'])
    def set_units(self,newunits):
        '''Установить единицу измерения newunits
        Значения:
            'K' - Кельвин
            'C' - градус Цельсия
            'F' - градус Фаренгейта'''
        #
        old=self.get_units()
        #
        if(old=='K')and(newunits=='C'):
            self.add_value(-273)
        elif(old=='C')and(newunits=='K'):
            self.add_value(273)
        if(old=='C')and(newunits=='F'):
            self.mul_value(9/5)
            self.add_value(32)
        elif(old=='F')and(newunits=='C'):
            self.add_value(-32)
            self.mul_value(5/9)
        super().set_units(newunits)
    #
#
#
#
class pressure(chem_parametr):
    '''Параметр давление'''
    #
    def __init__(self,value):
        chem_parametr.__init__(self,'pressure','Pa',value,100000)
        self.set_lstunits(['Pa','bar','at'])
    #
    def set_units(self,newunits):
        '''Установить единицу измерения newunits
        Значения:
            'Pa' - Паскаль
            'bar' - Бар
            'at' - атмосфера'''
        #
        old=self.get_units()
        #
        if(old=='Pa')and(newunits=='bar'):
            self.mul_value(0.00001)
        elif(old=='bar')and(newunits=='Pa'):
            self.mul_value(100000)
        if(old=='Pa')and(newunits=='at'):
            self.mul_value(1/101325)
        elif(old=='at')and(newunits=='Pa'):
            self.mul_value(101325)
        super().set_units(newunits)
    #
#
#
#
class volume(chem_parametr):
    '''Объем'''
    #
    def __init__(self,value):
        chem_parametr.__init__(self,'volume','m3',value,1)
    #
#
#
class area(chem_parametr):
    '''Площадь'''
    #
    def __init__(self,value):
        chem_parametr.__init__(self,'area','m2',value,1)
    #
#
#Функции
#
def getsumbols(frm):
    '''Функция позволяет получить список символов для матрицы элементов
    frm - строка формула вещества'''
    #
    result=[]
    uk={'root':result,'this':result,'history':[result]}
    #
    grpur=0
    grpind=0
    #
    for s in frm:
        if s.isupper():
            if len(uk['history'])-grpur+1>2:
                uk['history'].pop(-1)
                uk['this']=uk['history'][-1]
            uk['this'].append([])
            uk['this']=uk['this'][-1]
            uk['history'].append(uk['this'])
            uk['this'].append(s)
        elif s.islower():
            uk['this'].append(s)
        elif s.isdigit():
            uk['this'].append(s)
        elif(s=='(')or(s=='['):
            if len(uk['history'])>1:
                uk['history'].pop(-1)
                uk['this']=uk['history'][-1]
            uk['this'].append([])
            uk['this']=uk['this'][-1]
            uk['history'].append(uk['this'])
            grpur+=1
        elif(s==')')or(s==']'):
            uk['history'].pop(-1)
            uk['this']=uk['history'][-1]
            grpur-=1
    #
    if(grpur!=0):
        msg_error={'error':True,'typeerror':'syntaxis'}
    return result
#
def gettreematrix(lstsumbols):
    '''Метод позволяет получить структурированную элементную матрицу для вещества
    lstsumbols - список симвлов, подготовленный функцией getsumbols(frm)'''
    #
    result=[]
    str_el=''
    str_ind=''
    for el in lstsumbols:
        if isinstance(el,list):
            result.append(gettreematrix(el))
        elif isinstance(el,str):
            if el.isalpha():
                str_el+=el
            elif el.isdigit():
                str_ind+=el
    if str_ind=='':
        str_ind=1
    else:
        str_ind=int(str_ind)
    if str_el=='':
        result.append(str_ind)
    else:
        result.extend([str_el,str_ind])
    return result
#
def getsimplifymatrix(lstfrm):
    '''Функция для получения упрощенной элементной матрицы
    lstfrm - древовидная матрица, подготовленная функцией gettreematrix()'''
    #
    result={}
    if isinstance(lstfrm[0],list):
        add=map(lambda els:getsimplifymatrix(els[0:-1]+[els[-1]*lstfrm[-1]]),lstfrm[0:-1])
        for frm in add:
            for k,v in frm.items():
                if k in result:
                    result[k]+=v
                else:
                    result[k]=v

    elif isinstance(lstfrm[0],str):
        result={lstfrm[0]:lstfrm[-1]}
    return result
#
def to_substmatrix(frm,tp=1):
    '''Функция для получения элементной матрицы вещества
    возвращает словарь {<элемент>:<индекс>}
    frm - формула вещества
    tp - тип матрицы
        tp=1 - упрощенная
        tp=2 - древовидная'''
    #
    if tp==1:
        return getsimplifymatrix(gettreematrix(getsumbols(frm)))
    else:
        return gettreematrix(getsumbols(frm))
#
def to_formula(frm,prn_format='html'):
    '''Возвращает html представление формулы вещества
    frm - строка формулы вещества ('Fe2O3','Fe2(SO4)3',...)
    prn_format - параметр, определяющий представление фомулы ('html', 'tex', 'txt')'''
    #
    if prn_format=='txt':
        res=frm.strip()
    else:
        if prn_format=='html':
            sep_begin='<sub>'
            sep_end='</sub>'
        elif prn_format=='tex':
            sep_begin='_{'
            sep_end='}'
        #
        sumbols=list(frm+' ')
        res=''
        i_begin=0
        i_end=len(sumbols)-1
        for i in range(i_begin,i_end):
            s1=sumbols[i]
            s2=sumbols[i+1]
            if (not s1.isdigit())and(s2.isdigit()):
                res+=s1+sep_begin
            elif(s1.isdigit())and(not s2.isdigit()):
                res+=s1+sep_end
            else:
                res+=s1
    return res
#
def to_stmatrix(name=None,tp=1):
    '''Функция, преобразующая строку с описанием реакции в стехеометрическую матрицу
    name - строка - представление реакции
    tp - параметр, определяющий тип выводимой матрицы
        tp=1 список кортежей [(<коэффициент>,<формула>,<фаза>),]
        tp=2 - словарь {<формула>:<коэффициент>,}'''
    #
    res=[]
    if isinstance(name,str):
        if name.count('=')==1:
            clear_name=name.replace(',','.').replace(' ','').split('=')
            left_subst,right_subst=(s.split('+') for s in clear_name)
            lst_subst=['-'+s for s in left_subst]+right_subst
            for frm in lst_subst:
                k=0
                while(frm[k] not in string.ascii_uppercase):
                    k+=1
                if(frm[:k]=='-'):
                    koeff=-1
                elif(frm[:k]==''):
                    koeff=1
                else:
                    koeff=float(frm[:k])
                #
                p=-1
                if frm[p]==')':
                    while(frm[p]!='('):
                        p-=1
                    phase=frm[p:].replace('(','').replace(')','')
                else:
                    phase=None
                    p=len(frm)
                #
                formula=frm[k:p]
                res.append((koeff,formula,phase))
            #
            if tp==2:
                res={el[1]:el[0] for el in res}

    return res
#
def main():
    print('Модуль термодинамических расчетов. Версия 1.0')
if __name__ == '__main__':
    main()
