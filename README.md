# html2pdfptx

Программа работает через локальное веб-приложение. На вход принимает HTML-файл с интерактивной
презентацией на JavaScript, на выходе отдаёт PDF или PPTX.

## Пример работы

Все тестовые файлы лежат в папке `тестовые файлы`, там же лежат архивированные результаты конвертации в .pdf и .pptx.

### custom-js.html конвертация в .pptx

<table>
<tr>
<td align="center">Входной файл .html</td>
<td align="center">Работа приложения</td>
<td align="center">Выходной файл .pptx</td>
</tr>
<tr>
<td><img width="352" height="180" alt="image" src="https://github.com/user-attachments/assets/1131433c-9ad2-487d-a1fd-58dd0dd8ff32" /></td>
<td><img width="140" height="180" alt="image" src="https://github.com/user-attachments/assets/440fa458-b5dd-4c84-9a1e-74fdb8c55a61" /></td>
<td><img width="384" height="180" alt="image" src="https://github.com/user-attachments/assets/e8432037-0c4c-4da4-aadd-cb8696f589f0" /></td>
</tr>
</table>

### impress.js конвертация в .pdf

<table>
<tr>
<td align="center">Входной файл .zip</td>
<td align="center">Работа приложения</td>
<td align="center">Выходной файл .pdf</td>
</tr>
<tr>
<td><img width="321" height="180" alt="image" src="https://github.com/user-attachments/assets/b662514a-b85a-4772-8e75-23f0fadb3d5d" /></td>
<td><img width="95" height="180" alt="image" src="https://github.com/user-attachments/assets/66b2a4b8-d50f-430c-a9de-7ef4d5b28a20" /></td>
<td><img width="184" height="180" alt="image" src="https://github.com/user-attachments/assets/1032567d-3c77-452f-bcf4-86a382d83c44" /></td>
</tr>
</table>

### reveal-demo.zip конвертация в .pptx

<table>
<tr>
<td align="center">Входной файл .zip</td>
<td align="center">Работа приложения</td>
<td align="center">Выходной файл .pptx</td>
</tr>
<tr>
<td><img width="320" height="180" alt="image" src="https://github.com/user-attachments/assets/8193b88e-81d7-4ed6-b4be-7c6dbaa0b7fd" /></td>
<td><img width="87" height="180" alt="image" src="https://github.com/user-attachments/assets/8ba20cf9-1698-4f07-ba29-6c33c2102346" /></td>
<td><img width="371" height="180" alt="image" src="https://github.com/user-attachments/assets/9a542a7a-c21f-4471-a585-af2d4a6825b3" /></td>
</tr>
</table>

## Перед работой нам надо

### 1. Установить зависимости

```
pip install -r requirements.txt
```

### 2. Скачать браузер для Playwright

Презентация открывается в невидимом браузере Chromium, его нужно скачать один раз:

```
python -m playwright install chromium
```

## Как запустить

Запуск выполняется через `start.bat` (он сам поставит зависимости и браузер), либо через командную строку

```
python run.py
```

Далее открываем приложение в браузере http://127.0.0.1:5000
Выбираем файл, при необходимости меняем параметры и нажимаем "Конвертировать".
Когда слайды сняты, лишние можно убрать щелчком по миниатюре и скачать PDF или PPTX.

## Что важно знать

- Принимает `.html` или `.zip` (если у презентации рядом лежат свои картинки, стили и скрипты).
- Режимов три: "Авто", "Листать клавишей" и "Прокрутка страницы". Обычно хватает "Авто".
- "Авто" сам распознаёт reveal.js, impress.js, remark.js и Swiper и листает их через их API,
  а остальное листает клавишей. Если клавиши не листают - переходит на прокрутку.
- "Листать клавишей" - для самописных презентаций (→, ↓, PageDown, пробел или клик). Каждый слайд
  снимается, когда закончилась анимация. Конец - когда картинка перестала меняться
  или презентация вернулась к первому слайду.
- "Прокрутка страницы" снимает блоки-слайды (`.slide`, `section` и т.п.), а если их нет -
  режет страницу по экранам.
- Слайды сохраняются картинками: текст в PPTX нельзя редактировать. Видимый текст слайда
  и заметки докладчика из reveal.js попадают в заметки PowerPoint.
- Если на слайдах долгие анимации - увеличьте паузу после перехода.

## Структура проекта

- `run.py` - запускает приложение
- `app/server.py` - веб-сервер на Flask, принимает файл, отдаёт миниатюры и готовый файл
- `app/unpack.py` - сохраняет загруженный HTML или распаковывает .zip
- `app/capture.py` - открывает презентацию в браузере и снимает слайды
- `app/build_pdf.py` - собирает PDF
- `app/build_pptx.py` - собирает PPTX
- `app/templates/index.html`, `app/static/` - веб-часть
- `тестовые файлы/` - примеры презентаций для проверки:
  - `custom-js.html` - произвольная презентация на JavaScript 
  - `reveal.html` - презентация на reveal.js 
  - `reveal-demo.zip` - официальное демо [reveal.js](https://github.com/hakimel/reveal.js) 6.0.2, 41 слайд
  - `impress-demo.zip` - официальное демо [impress.js](https://github.com/impress/impress.js) 2.0.0, 13 слайдов
  - `remark-demo.zip` - сайт [remarkjs.com](https://github.com/gnab/remark), сам сделанный на remark, 19 слайдов
