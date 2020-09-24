Поиск треков под подходящий BPM.

Работает на python 3.7+

python -m venv venv
. venv/bin/activate

pip install -r requirements.txt

Для Google Music: сперва надо запустить gmusic-login и следовать указаниям.

./bpmcrawld.py -s gmusic [--station URL | -p playlist_name]
Будет извлекать (путём расчёта) из всех треков информацию о BPM и сохранять в histogram.db
Для Google Music по умолчанию будет обрабатывать станцию I'm Feeling Lucky (IFL).
Можно запускать несколько раз - к примеру, Google Music в IFL может давать разные выдачи. Можно попробовать запускать периодически из cron, база будет наполняться по мере того, как изменяется выдача.

./bpmcrawl-pick.py найдёт в histogram.db все треки, подходящие под нужный BPM, и зальёт их в playlist с названием bpmcrawl.
Если трек уже есть в playlist - добавлять не будет (это можно переопределить параметром -r)

Т.е. сценарий запуска - сперва bpmcrawld, затем bpmcrawl-pick.

Если при использовании Google Music вдруг начала появляться ругань в духе Access Denied или вроде того, можно попробовать перелогиниться в Google Music.
Для этого надо удалить файл ~/.local/share/gmusicapi/mobileclient.cred и запустить ./gmusic-login.py

