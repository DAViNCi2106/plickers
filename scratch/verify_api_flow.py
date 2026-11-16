import urllib.request
import json

def req(url, data=None, token=None, method=None):
    r = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers={
            'Content-Type': 'application/json',
            **({'Authorization': f'Bearer {token}'} if token else {})
        },
        method=method
    )
    with urllib.request.urlopen(r) as res:
        return json.loads(res.read().decode())

# 1. Login
tok = req('http://127.0.0.1:8000/api/v1/auth/login', {'username': 'anil.kumar@demohighschool.edu', 'password': 'Teacher@1234'})['data']['access_token']
print('[OK] Login successful')

# 2. Get Question Set 1 detail
qs1 = req('http://127.0.0.1:8000/api/v1/schools/1/question-sets/1', token=tok)['data']
print(f'[OK] Question Set 1 loaded: "{qs1["title"]}", questions count = {len(qs1.get("questions", []))}')

# 3. Test get questions endpoint directly
qs_list = req('http://127.0.0.1:8000/api/v1/schools/1/question-sets/1/questions', token=tok)['data']
print(f'[OK] /questions endpoint loaded: {len(qs_list)} questions')

# 4. Quick quiz create
qq = req('http://127.0.0.1:8000/api/v1/schools/1/question-sets/quick-create', {
    'title': 'Automated Verification Quiz',
    'subject': 'Science',
    'grade': 'Grade 10',
    'questions': [
        {'correct_answer': 'A', 'question_text': 'What is H2O?', 'option_a': 'Water', 'option_b': 'Oxygen', 'option_c': 'Hydrogen', 'option_d': 'Carbon', 'marks': 1}
    ]
}, token=tok)['data']
print(f'[OK] Quick Quiz created with ID {qq["question_set_id"]}')

# 5. Create & start session
sess = req('http://127.0.0.1:8000/api/v1/schools/1/quiz-sessions', {
    'question_set_id': qq['question_set_id'],
    'class_id': 1
}, token=tok)['data']
print(f'[OK] Quiz session created with ID {sess["id"]}, status = {sess["status"]}')

started_sess = req(f'http://127.0.0.1:8000/api/v1/schools/1/quiz-sessions/{sess["id"]}/start', token=tok, method='POST')['data']
print(f'[OK] Quiz session started: ID {started_sess["id"]}, status = {started_sess["status"]}')

# 6. Fetch questions for the started session
qq_detail = req(f'http://127.0.0.1:8000/api/v1/schools/1/question-sets/{qq["question_set_id"]}', token=tok)['data']
print(f'[OK] Questions for newly started session: {len(qq_detail.get("questions", []))} question(s) loaded successfully!')
