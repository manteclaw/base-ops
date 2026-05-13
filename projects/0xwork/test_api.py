import urllib.request
import json

url = 'https://api.0xwork.org/tasks?status=Open'
req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Manteclaw-TaskMatcher/1.0'})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    tasks = data.get('tasks', data) if isinstance(data, dict) else data
    tasks = tasks if isinstance(tasks, list) else []
    print('Tasks found:', len(tasks))
    for t in tasks:
        print(f"  ID {t.get('id')}: {t.get('category')} - ${t.get('bounty_amount')} - {t.get('status')}")
