import requests
from bs4 import BeautifulSoup as bs
import telebot
from telebot import types
import typing_extensions
import re

#экземпляры класса City будут создаваться при выборе конкретного города и будут иметь атрибуты 
#паме - название города
#list_href - список ссылок на экскурсии в городе
#counter - счетчик просмотренных экскурсий
class City:
  lst = []  #в этот список будут добавляться объекты класса, созданные при выборе города из списка названий городов, в которых проводятся экскурсии
  def __init__(self, name, list_href):
    self.name = name  #название города
    self.list_href = list_href  #список экскупсий в городе
    self.counter = 0  #счетчик экскурсий в городе
  

  def add_city(self):
    City.lst.append(self)  #в список просмотренных городов добавляется выбранный город
  

  @classmethod
  def last_city(cls):
    if cls.lst != []:
      return cls.lst[-1]  #возвращается объект класса последнего выбранного для просмотра города


#функция возвращает список ссылок на все экскурсии конкретного города
def make_list_href(city):  #на вход принимается название города - строка
  r_city = requests.get(d[city])
  soup_city = bs(r_city.text, 'html5lib')
  href_city_ex = ['https://www.sputnik8.com' + ex.find('a')['href'] for ex in soup_city.find_all('div', {'class': 'activity-card-cover__overlay-content'})]
  return href_city_ex


#функция для сбора данных по каждой экскурсии
#функция возвращает словарь, ключи - наименования пунктов описания экскурсии, значения - соответствующая информация, полученная при парсинге страницы
def ex_describe(html):
  r_ex = requests.get(html)
  soup_ex = bs(r_ex.text, 'html5lib')
  ex_dict = {}
  ex_title_1 = soup_ex.find('h1', {'class': 'bem-heading bem-heading_h2 activity-header__title'})
  ex_title_2 = soup_ex.find('h1', {'class': 'bem-heading bem-heading_h2 activity-header__title activity-header__title_theme-sputnik-plus'})
  ex_title = ex_title_1 if ex_title_1 is not None else ex_title_2
  ex_rev = soup_ex.find('div', {'class': 'bem-paragraph bem-paragraph_no-margin bem-paragraph_weight-bold bem-heap__item'})
  ex_rating = soup_ex.find('div', {'class': 'bem-short-rating_size-big'})
  ex_type = soup_ex.find('div', {'class': 'activity-highlights__item activity-highlights__item_size-big activity-highlights__item_color-semi-black activity-highlights__item_hl-flag'})
  ex_time = soup_ex.find('div', {'class': 'activity-highlights__item activity-highlights__item_size-big activity-highlights__item_color-semi-black activity-highlights__item_hl-clock'})
  ex_count = soup_ex.find('div', {'class': 'activity-highlights__item activity-highlights__item_size-big activity-highlights__item_color-semi-black activity-highlights__item_hl-ppl'})
  ex_lang = soup_ex.find('div', {'class': 'activity-highlights__item activity-highlights__item_size-big activity-highlights__item_color-semi-black activity-highlights__item_hl-lang'})
  ex_price = soup_ex.find('span', {'class': 'bem-price bem-price_size-medium-small gtm-activity-card-price js-currency-switcher js-activity-card-base-price bem-price_size-big'})
  ex_price_d = soup_ex.find('div', {'class': 'js-activity-price-type bem-price-type bem-price-type_size-big'})
  ex_descr = soup_ex.find('div', {'class': 'bem-paragraph bem-paragraph_no-margin bem-paragraph_size-large bem-paragraph_color-light-black'})
  ex_dict['Название экскурсии'] = ex_title.text.strip() if ex_title is not None else 'Информация отсутствует'
  ex_dict['Описание экскурсии'] = ex_descr.text.strip() if ex_descr is not None and ex_descr.text.strip() != '' else 'Информация отсутствует'
  ex_dict['Количество отзывов'] = int(ex_rev.text.strip()[:ex_rev.text.strip().index(' ')]) if ex_rev is not None else 0
  ex_dict['Рейтинг от 0 до 5'] = float(ex_rating.text.strip()) if ex_rating is not None else 0.0
  ex_dict['Тип экскурсии'] = ex_type.text.strip() if ex_type is not None else 'Информация отсутствует'
  ex_dict['Продолжительность'] = ex_time.text.strip() if ex_time is not None else 'Информация отсутствует'
  ex_dict['Размер группы до (чел.)'] = int(re.findall(r'\d+', ex_count.text.strip())[0]) if ex_count is not None else 'Информация отсутствует'
  ex_dict['Язык'] = ex_lang.text.strip()[: ex_lang.text.strip().index(' ')] if ex_lang is not None else 'Информация отсутствует'
  ex_dict['Цена'] = ex_price.text[:-1] + 'руб. ' + ex_price_d.text
  ex_dict['Ссылка на экскурсию'] = html
  return ex_dict


#функция для создания информационного сообщения об экскурсии
#в качестве аргумента принимает словарь с описанием экскурсии
#возвращает строку, которая передается затем как сообщение в во время работы Телеграм-бота
def make_message_ex(ex_dict):
  mes = ''
  i = 1
  for key in ex_dict:
    mes += f'{i}. {key}: {ex_dict[key]}' + '\n'
    i += 1
  return mes


r = requests.get('https://www.sputnik8.com/ru/countries/russia')
if r.status_code == 200:
  soup = bs(r.text, 'html5lib')
  cities = soup.find_all('div', {'class': 'city-country-card lazy'})
#загружаем ссылки на экскурсии в городах России
d = {}
for city in cities:
  name_city = city.find('a', {'class': 'city-country-card__title'})
  city_href = city.select_one('a')['href']
  if (not city_href.startswith('/ru')) and name_city.text.strip() != 'service-city':
    d[name_city.text.strip()] = city_href


bot = telebot.TeleBot(TOKEN)


#обработчик команд start и help
@bot.message_handler(commands=['start', 'help'])
def start(message, res=False):
  mes_start = ''
  for c in sorted(list(d.keys())):
    mes_start = mes_start + '\n' + c
  bot.send_message(message.chat.id, mes_start + '\n\n' + '''* Введите название города из списка выше для поиска экскурсии\n\n* Введите
  команду /help для получения справки\n\n* Нажмите кнопку "Следующая экскурсия" 
  для перехода к просмотру следующей экскурсии в выбранном городе\n\n* Нажмите кнопку "Предыдущая экскурсия" 
  для перехода к просмотру предыдущей экскурсии в выбранном городе''')


#обработчик сообщений
@bot.message_handler(content_types=['text'])
def handler_text(message):
  text = message.text.strip()
  if text in list(d.keys()):
    list_href = make_list_href(text)
    city = City(text, list_href)  #создается экземпляр класса для выбранного города, в качестве аргументов передается название города и список экскурсии в этом городе
    if len(city.list_href) != 0:
      href = city.list_href[city.counter]
      City.add_city(city)  #добавление в список просмотренных городов объекта класса для выбранного города
    mark = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if len(city.list_href) > 1:
      mes = make_message_ex({**{'Город': city.name}, **ex_describe(href)})
      item2 = types.KeyboardButton('Следующая экскурсия')  #выводится, если в выбранном городе несколько экскурсий
      mark.add(item2)
    elif len(city.list_href) == 1:
      mes = make_message_ex({**{'Город': city.name}, **ex_describe(href)})  #если в городе одна экскурсия, то кнопка "Следующая экскурсия" не выводится
    else:
      mes = 'В этом городе пока не проводятся экскурсии'
    bot.send_message(message.chat.id, mes, reply_markup=mark)
  elif text == 'Следующая экскурсия':  #выбрана кнопка "Следующая экскурсия"
    City.last_city().counter += 1  #счетчик экскурсий города увеличиается на 1
    href = City.last_city().list_href[City.last_city().counter]  #выбор ссылки на следующую экскурсию
    mes = make_message_ex({**{'Город': City.last_city().name}, **ex_describe(href)})
    mark = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if City.last_city().counter != len(City.last_city().list_href)-1:
      item1 = types.KeyboardButton('Предыдущая экскурсия')  #выводятся кнопки "Следующая экскурсия", "Предыдущая экскурсия" пока не дошли до последней экскурсии в списке
      item2 = types.KeyboardButton('Следующая экскурсия')
      mark.add(item1)
      mark.add(item2)
    else:
      item1 = types.KeyboardButton('Предыдущая экскурсия')  #выводится только кнопка "Предыдущая экскурсия", если дошли до последней экскурсии в списке
      mark.add(item1)
    bot.send_message(message.chat.id, mes, reply_markup=mark)
  elif text == 'Предыдущая экскурсия':  #выбрана кнопка "Предыдующая экскурсия"
    City.last_city().counter -= 1  #счетчик экскурсий города уменьшается на 1
    href = City.last_city().list_href[City.last_city().counter]  #выбор ссылки на предыдующую экскурсию
    mes = make_message_ex({**{'Город': City.last_city().name}, **ex_describe(href)})
    mark = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if City.last_city().counter != 0:
      item1 = types.KeyboardButton('Предыдущая экскурсия')  #выводятся кнопки "Следующая экскурсия", "Предыдущая экскурсия" пока не дошли до первой экскурсии в списке
      item2 = types.KeyboardButton('Следующая экскурсия')
      mark.add(item1)
      mark.add(item2)
    else:
      item2 = types.KeyboardButton('Следующая экскурсия')  #выводится только кнопка "Следующая экскурсия", если дошли до первой экскурсии в списке
      mark.add(item2)
    bot.send_message(message.chat.id, mes, reply_markup=mark)
  elif text not in list(d.keys()):
    mes = 'Этого города нет в списке. Введите новое название'
    bot.send_message(message.chat.id, mes)


bot.infinity_polling()
