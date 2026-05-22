import requests
s = requests.Session()
r1 = s.post('http://localhost:8888/login', data={'username':'endoneko', 'password':'endoneko'})
r2 = s.get('http://localhost:8888/playground')
with open('test_res.html', 'w', encoding='utf-8') as f:
    f.write(str(r2.status_code) + '\n' + r2.text)
