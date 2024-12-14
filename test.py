
import json

text = """{
    "propositions": [
        "晨間運動的好處"
    ]
}"""

js = json.loads(text)

print(js)