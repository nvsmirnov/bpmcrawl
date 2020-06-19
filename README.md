Работает на python 3.7+

python -m venv venv
. venv/bin/activate

pip install -r requirements.txt

Сперва надо запустить gmusic-login и следовать указаниям.

./bpmcrawld.py [station URL]
Будет извлекать из всех треков информацию о BPM и сохранять в histogram.db
По умолчанию будет обрабатывать станцию I'm Feeling Lucky

./bpmcrawl-pick.py найдёт в histogram.db все треки, подходящие под нужный BPM
